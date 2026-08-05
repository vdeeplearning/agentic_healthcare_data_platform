"""Explicit developer commands for the local lake lifecycle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import Settings
from src.lake.models import LakeLayer
from src.lake.pipeline import LocalLakePipeline
from src.lake.serving import publish_gold_to_postgres, publish_gold_to_sqlite
from src.lake.store import LocalFilesystemLakeStore
from src.metadata.repository import SQLiteManifestStore


def _print(value):
    if hasattr(value,"model_dump"): value=value.model_dump(mode="json")
    print(json.dumps(value,indent=2,default=lambda item:item.model_dump(mode="json") if hasattr(item,"model_dump") else str(item)))


def main()->None:
    parser=argparse.ArgumentParser(description="Deterministic local raw/bronze/silver/gold pipeline")
    parser.add_argument("--root",type=Path,default=None); commands=parser.add_subparsers(dest="command",required=True)
    generate=commands.add_parser("generate-source"); generate.add_argument("--profile",choices=("test","demo","full"),default="test"); generate.add_argument("--seed",type=int,default=17); generate.add_argument("--kind",choices=("initial","incremental"),default="initial"); generate.add_argument("--parent-batch-id"); generate.add_argument("--malformed",action="store_true")
    raw=commands.add_parser("publish-raw"); raw.add_argument("--batch-id",required=True)
    transform=commands.add_parser("transform"); transform.add_argument("--input-snapshot-id",required=True); transform.add_argument("--to",choices=("bronze","silver","gold"),required=True); transform.add_argument("--version")
    run=commands.add_parser("run-pipeline"); run.add_argument("--profile",choices=("test","demo","full"),default="test"); run.add_argument("--seed",type=int,default=17)
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
    elif args.command=="transform": _print(pipeline.transform(args.input_snapshot_id,LakeLayer(args.to),args.version))
    elif args.command=="run-pipeline": _print(pipeline.run(args.profile,args.seed))
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
