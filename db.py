import psycopg2
from psycopg2.extras import RealDictCursor
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "logpulse")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )

def log_incident_and_get_context(service_name: str, level: str, message: str, cpu: float, memory: float):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Servisi getir veya yoksa ekle
            cur.execute("SELECT id, max_memory_mb, max_cpu_percent, tier FROM services WHERE name = %s;", (service_name,))
            svc = cur.fetchone()
            if not svc:
                cur.execute(
                    "INSERT INTO services (name) VALUES (%s) RETURNING id, max_memory_mb, max_cpu_percent, tier;",
                    (service_name,)
                )
                svc = cur.fetchone()

            service_id = svc["id"]

            # 2. Olayı incident_logs tablosuna yaz
            cur.execute("""
                INSERT INTO incident_logs (service_id, level, message, cpu_usage, memory_usage)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """, (service_id, level, message, cpu, memory))
            incident_id = cur.fetchone()["id"]
            conn.commit()

            # 3. ÇOK TABLOLU JOIN: Servis limitleri + Son 1 saatteki hata sayısı + Son operatör müdahalesi
            cur.execute("""
                SELECT 
                    s.name AS service_name,
                    s.max_memory_mb,
                    s.max_cpu_percent,
                    s.tier,
                    COUNT(DISTINCT il.id) AS total_incidents_last_hour,
                    ra.action_taken AS last_remediation_action,
                    ra.execution_status AS last_remediation_status,
                    ra.approved_by AS last_operator
                FROM services s
                LEFT JOIN incident_logs il 
                    ON s.id = il.service_id 
                    AND il.created_at >= NOW() - INTERVAL '1 HOUR'
                LEFT JOIN remediation_audits ra 
                    ON s.id = ra.service_id 
                    AND ra.created_at = (
                        SELECT MAX(created_at) FROM remediation_audits WHERE service_id = s.id
                    )
                WHERE s.id = %s
                GROUP BY s.id, ra.action_taken, ra.execution_status, ra.approved_by;
            """, (service_id,))
            
            context_graph = cur.fetchone()
            return incident_id, context_graph
    finally:
        conn.close()

def log_audit_action(incident_id: int, service_name: str, action: str, operator: str = "operator_admin"):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM services WHERE name = %s;", (service_name,))
            res = cur.fetchone()
            if res:
                service_id = res[0]
                cur.execute("""
                    INSERT INTO remediation_audits (incident_id, service_id, action_taken, approved_by, execution_status)
                    VALUES (%s, %s, %s, %s, 'SUCCESS');
                """, (incident_id, service_id, action, operator))
                conn.commit()
    finally:
        conn.close()