"""Controlled, lazy Spark session lifecycle with actionable capability errors."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


class SparkUnavailableError(RuntimeError): pass


@dataclass(frozen=True)
class SparkSessionSettings:
    master: str = "local[*]"
    application_name: str = "agentic-healthcare-lake"
    shuffle_partitions: int = 4
    log_level: str = "WARN"
    warehouse_dir: Path | None = None

    def validate(self)->None:
        if not self.master.strip(): raise ValueError("Spark master must not be empty.")
        if self.shuffle_partitions<1: raise ValueError("Spark shuffle partitions must be positive.")
        if self.log_level.upper() not in {"ALL","DEBUG","ERROR","FATAL","INFO","OFF","TRACE","WARN"}: raise ValueError("Unsupported Spark log level.")


class SparkSessionFactory:
    def __init__(self,settings:SparkSessionSettings): self.settings=settings; self._session=None

    @staticmethod
    def capability()->dict[str,str|bool|None]:
        try:
            import pyspark
            version=pyspark.__version__
        except ImportError: return {"available":False,"pyspark_version":None,"java":shutil.which("java"),"reason":"Install `.[spark]`."}
        java=shutil.which("java") or (str(Path(os.environ["JAVA_HOME"])/"bin"/"java") if os.environ.get("JAVA_HOME") else None)
        return {"available":bool(java),"pyspark_version":version,"java":java,"reason":None if java else "Java 17+ was not found; set JAVA_HOME or PATH."}

    def create(self):
        self.settings.validate(); capability=self.capability()
        if not capability["available"]: raise SparkUnavailableError(str(capability["reason"]))
        major_minor=tuple(int(part) for part in str(capability["pyspark_version"]).split(".")[:2])
        if major_minor<(3,5) or major_minor>=(4,1): raise SparkUnavailableError(f"Unsupported PySpark version: {capability['pyspark_version']}; supported >=3.5,<4.1.")
        try:
            from pyspark.sql import SparkSession
            builder=SparkSession.builder.appName(self.settings.application_name).master(self.settings.master).config("spark.sql.session.timeZone","UTC").config("spark.sql.shuffle.partitions",str(self.settings.shuffle_partitions)).config("spark.sql.adaptive.enabled","false")
            if self.settings.warehouse_dir: builder=builder.config("spark.sql.warehouse.dir",self.settings.warehouse_dir.resolve().as_uri())
            self._session=builder.getOrCreate(); self._session.sparkContext.setLogLevel(self.settings.log_level.upper()); return self._session
        except Exception as exc: raise SparkUnavailableError(f"Spark session startup failed: {exc}") from exc

    def stop(self)->None:
        if self._session is not None: self._session.stop(); self._session=None

    def __enter__(self): return self.create()
    def __exit__(self,*_): self.stop()
