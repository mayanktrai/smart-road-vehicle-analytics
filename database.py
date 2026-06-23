"""MySQL persistence layer.

Writes detections, speed violations and ANPR results; provides aggregate queries
for the dashboard. Degrades gracefully: if the DB is disabled or unreachable, writes
become no-ops and reads return empty results, so the pipeline keeps running.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

log = logging.getLogger("database")


class Database:
    def __init__(self, cfg) -> None:
        d = cfg.get("database", {}) or {}
        self.enabled = bool(d.get("enabled", True))
        self._conn = None
        self._params = {
            "host": d.get("host", "127.0.0.1"),
            "port": int(d.get("port", 3306)),
            "user": d.get("user", "root"),
            "password": d.get("password", ""),
            "database": d.get("database", "road_analytics"),
        }
        if self.enabled:
            self._connect()

    def _connect(self) -> None:
        try:
            import mysql.connector

            self._conn = mysql.connector.connect(autocommit=True, **self._params)
            log.info("Connected to MySQL at %s", self._params["host"])
        except Exception as exc:  # pragma: no cover - environment dependent
            log.warning("MySQL unavailable (%s); DB writes/reads disabled.", exc)
            self._conn = None

    @property
    def connected(self) -> bool:
        return self._conn is not None

    def _cursor(self, dictionary: bool = False):
        if not self.connected:
            return None
        try:
            if not self._conn.is_connected():
                self._conn.reconnect(attempts=2, delay=1)
        except Exception:  # pragma: no cover
            return None
        return self._conn.cursor(dictionary=dictionary)

    # ---- writes -----------------------------------------------------------
    def insert_vehicle(
        self,
        track_id: Optional[int],
        category: str,
        yolo_class: str,
        confidence: float,
    ) -> Optional[int]:
        cur = self._cursor()
        if cur is None:
            return None
        try:
            cur.execute(
                "INSERT INTO vehicles (track_id, category, yolo_class, confidence) "
                "VALUES (%s, %s, %s, %s)",
                (track_id, category, yolo_class, confidence),
            )
            return cur.lastrowid
        except Exception as exc:  # pragma: no cover
            log.error("insert_vehicle failed: %s", exc)
            return None
        finally:
            cur.close()

    def insert_violation(
        self, vehicle_id: int, logged_speed: float, speed_limit: float
    ) -> None:
        cur = self._cursor()
        if cur is None:
            return
        try:
            cur.execute(
                "INSERT INTO speed_violations (vehicle_id, logged_speed, speed_limit) "
                "VALUES (%s, %s, %s)",
                (vehicle_id, logged_speed, speed_limit),
            )
        except Exception as exc:  # pragma: no cover
            log.error("insert_violation failed: %s", exc)
        finally:
            cur.close()

    def insert_anpr(
        self, vehicle_id: Optional[int], plate_text: str, confidence: float
    ) -> None:
        cur = self._cursor()
        if cur is None:
            return
        try:
            cur.execute(
                "INSERT INTO anpr_logs (vehicle_id, plate_text, confidence) "
                "VALUES (%s, %s, %s)",
                (vehicle_id, plate_text, confidence),
            )
        except Exception as exc:  # pragma: no cover
            log.error("insert_anpr failed: %s", exc)
        finally:
            cur.close()

    # ---- reads (dashboard) ------------------------------------------------
    def counts_by_category(self) -> Dict[str, int]:
        cur = self._cursor(dictionary=True)
        if cur is None:
            return {}
        try:
            cur.execute(
                "SELECT category, COUNT(*) AS n FROM vehicles GROUP BY category"
            )
            return {row["category"]: int(row["n"]) for row in cur.fetchall()}
        except Exception:  # pragma: no cover
            return {}
        finally:
            cur.close()

    def hourly_counts(self, hours: int = 24) -> List[Dict]:
        cur = self._cursor(dictionary=True)
        if cur is None:
            return []
        try:
            cur.execute(
                "SELECT DATE_FORMAT(detected_time, '%Y-%m-%d %H:00') AS hour, "
                "COUNT(*) AS n FROM vehicles "
                "WHERE detected_time >= NOW() - INTERVAL %s HOUR "
                "GROUP BY hour ORDER BY hour",
                (hours,),
            )
            return [{"hour": r["hour"], "count": int(r["n"])} for r in cur.fetchall()]
        except Exception:  # pragma: no cover
            return []
        finally:
            cur.close()

    def recent_violations(self, limit: int = 20) -> List[Dict]:
        cur = self._cursor(dictionary=True)
        if cur is None:
            return []
        try:
            cur.execute(
                "SELECT v.violation_id, v.logged_speed, v.speed_limit, v.violated_time, "
                "veh.category, veh.track_id "
                "FROM speed_violations v JOIN vehicles veh ON veh.id = v.vehicle_id "
                "ORDER BY v.violated_time DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
            for r in rows:
                r["violated_time"] = str(r["violated_time"])
                r["logged_speed"] = round(float(r["logged_speed"]), 1)
            return rows
        except Exception:  # pragma: no cover
            return []
        finally:
            cur.close()

    def summary(self) -> Dict:
        cur = self._cursor(dictionary=True)
        if cur is None:
            return {"total_vehicles": 0, "total_violations": 0, "total_plates": 0}
        try:
            cur.execute("SELECT COUNT(*) AS n FROM vehicles")
            vehicles = int(cur.fetchone()["n"])
            cur.execute("SELECT COUNT(*) AS n FROM speed_violations")
            violations = int(cur.fetchone()["n"])
            cur.execute("SELECT COUNT(*) AS n FROM anpr_logs")
            plates = int(cur.fetchone()["n"])
            return {
                "total_vehicles": vehicles,
                "total_violations": violations,
                "total_plates": plates,
            }
        except Exception:  # pragma: no cover
            return {"total_vehicles": 0, "total_violations": 0, "total_plates": 0}
        finally:
            cur.close()

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:  # pragma: no cover
                pass
