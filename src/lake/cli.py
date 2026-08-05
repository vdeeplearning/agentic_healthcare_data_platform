"""Explicit developer commands for the local lake lifecycle."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from src.config import Settings
from src.lake.models import LakeLayer
from src.lake.pipeline import LocalLakePipeline
from src.lake.serving import publish_gold_to_postgres, publish_gold_to_sqlite
from src.lake.store import LocalFilesystemLakeStore
from src.lake.engines import create_transformation_engine
from src.lake.parity import run_engine_parity,write_report
from src.lake.spark_session import SparkSessionFactory,SparkSessionSettings
from src.metadata.repository import SQLiteManifestStore


def _print(value):
    if hasattr(value,"model_dump"): value=value.model_dump(mode="json")
    print(json.dumps(value,indent=2,default=lambda item:item.model_dump(mode="json") if hasattr(item,"model_dump") else str(item)))


def main()->None:
    parser=argparse.ArgumentParser(description="Deterministic local raw/bronze/silver/gold pipeline")
    parser.add_argument("--root",type=Path,default=None); commands=parser.add_subparsers(dest="command",required=True)
    profiles=("test","demo","full","spark-scale")
    generate=commands.add_parser("generate-source"); generate.add_argument("--profile",choices=profiles,default="test"); generate.add_argument("--seed",type=int,default=17); generate.add_argument("--kind",choices=("initial","incremental"),default="initial"); generate.add_argument("--parent-batch-id"); generate.add_argument("--malformed",action="store_true")
    raw=commands.add_parser("publish-raw"); raw.add_argument("--batch-id",required=True)
    transform=commands.add_parser("transform"); transform.add_argument("--input-snapshot-id",required=True); transform.add_argument("--to",choices=("bronze","silver","gold"),required=True); transform.add_argument("--version"); transform.add_argument("--engine",choices=("python","spark"),default=None)
    run=commands.add_parser("run-pipeline"); run.add_argument("--profile",choices=profiles,default="test"); run.add_argument("--seed",type=int,default=17); run.add_argument("--engine",choices=("python","spark"),default=None)
    parity=commands.add_parser("parity"); parity.add_argument("--profile",choices=profiles,default="test"); parity.add_argument("--seed",type=int,default=17); parity.add_argument("--report",type=Path,required=True)
    performance=commands.add_parser("spark-performance"); performance.add_argument("--profile",choices=("demo","full","spark-scale"),default="spark-scale"); performance.add_argument("--seed",type=int,default=17)
    commands.add_parser("spark-capability")
    listing=commands.add_parser("list"); listing.add_argument("--layer",choices=("raw","bronze","silver","gold"))
    validate=commands.add_parser("validate"); validate.add_argument("--manifest-id",required=True)
    sqlite=commands.add_parser("publish-sqlite"); sqlite.add_argument("--gold-snapshot-id",required=True); sqlite.add_argument("--path",type=Path,required=True)
    postgres=commands.add_parser("publish-postgres"); postgres.add_argument("--gold-snapshot-id",required=True); postgres.add_argument("--dsn"); postgres.add_argument("--schema",default="public"); postgres.add_argument("--metadata-path",type=Path,required=True)
    lineage=commands.add_parser("lineage"); lineage.add_argument("--snapshot-id",required=True)
    args=parser.parse_args(); settings=Settings(); store=LocalFilesystemLakeStore(args.root or settings.lake_root); pipeline=LocalLakePipeline(store)
    if args.command=="generate-source": _print(pipeline.generate_source(args.profile,args.seed,args.kind,args.parent_batch_id,args.malformed))
    elif args.command=="publish-raw":
        batch=store.get_source_batch(args.batch_id)
        if not batch: raise SystemExit(f"Unknown source batch: {args.batch_id}")
        _print(pipeline.publish_raw(batch))
    elif args.command=="transform":
        engine=create_transformation_engine(settings.model_copy(update={"lake_transform_engine":args.engine or settings.lake_transform_engine}),store)
        try: _print(pipeline.transform(args.input_snapshot_id,LakeLayer(args.to),args.version,engine))
        finally: engine.close()
    elif args.command=="run-pipeline":
        engine=create_transformation_engine(settings.model_copy(update={"lake_transform_engine":args.engine or settings.lake_transform_engine}),store)
        try: _print(pipeline.run(args.profile,args.seed,engine))
        finally: engine.close()
    elif args.command=="parity":
        engine=create_transformation_engine(settings.model_copy(update={"lake_transform_engine":"spark"}),store); report=run_engine_parity(store.root/"parity",args.profile,args.seed,engine); write_report(report,args.report); _print(report)
    elif args.command=="spark-performance":
        engine=create_transformation_engine(settings.model_copy(update={"lake_transform_engine":"spark"}),store); started=time.perf_counter()
        try: result=pipeline.run(args.profile,args.seed,engine)
        finally: engine.close()
        _print({"profile":args.profile,"elapsed_seconds":time.perf_counter()-started,"gold_snapshot_id":result["gold"].snapshot_id,"local_mode":settings.spark_master.startswith("local")})
    elif args.command=="spark-capability": _print(SparkSessionFactory(SparkSessionSettings()).capability())
    elif args.command=="list": _print([item.model_dump(mode="json") for item in store.list_layer_manifests(LakeLayer(args.layer) if args.layer else None)])
    elif args.command=="validate":
        manifest=store.get_layer_manifest(args.manifest_id)
        if not manifest: raise SystemExit(f"Unknown manifest: {args.manifest_id}")
        _print({"manifest_id":manifest.manifest_id,"validation":manifest.validation})
    elif args.command=="publish-sqlite": _print(publish_gold_to_sqlite(store,args.gold_snapshot_id,args.path))
    elif args.command=="publish-postgres":
        dsn=args.dsn or settings.postgres_dsn
        if not dsn: raise SystemExit("PostgreSQL publication requires --dsn or POSTGRES_DSN.")
        _print(publish_gold_to_postgres(store,args.gold_snapshot_id,dsn,SQLiteManifestStore(args.metadata_path),args.schema))
    else: _print([item.model_dump(mode="json") for item in store.resolve_parent_lineage(args.snapshot_id)])


if __name__=="__main__": main()
