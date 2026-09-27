"""Generate the APM dashboards: one per app plus the consolidated Environment APM.

Run from this directory after changing APPS, then commit the JSON it writes:

    python gen_apm.py

Per-app dashboards come from one template so they cannot drift apart. Sources:
- beyla:  Beyla eBPF metrics (http_server_request_duration_seconds, unsampled)
- traces: Tempo span metrics (traces_spanmetrics_*), for apps Beyla does not
          cover but that send their own OpenTelemetry traces (Keycloak)
Jellyfin keeps its hand-built dashboard (jellyfin-apm.json, .NET runtime row);
it only appears here in the consolidated view.
"""
import json

DS = {"type": "prometheus", "uid": "prometheus"}

# service = the service_name (beyla) or service (traces) label value.
# Only apps that actually emit spans get a dashboard. Beyla (the eBPF source) was
# rolled back after INC0044913, so "beyla" entries produced empty boards; they were
# removed 2026-09-27 and come back per app under CHG0030481 (OpenTelemetry Operator
# auto-instrumentation, opt-in per pod). RomM exports OTLP natively and names
# itself "api" in its spans.
APPS = [
    {"slug": "romm", "title": "RomM", "service": "api", "namespace": "romm", "container": "romm", "source": "traces"},
    {"slug": "keycloak", "title": "Keycloak", "service": "keycloak", "namespace": "keycloak", "container": "keycloak", "source": "traces"},
]

# Apdex thresholds sit on real bucket edges of each source.
APDEX = {
    "beyla": ("0.25", "1.0", "0.25s"),
    "traces": ("0.512", "2.048", "0.512s"),
    "jellyfin": ("0.256", "1.024", "0.256s"),
}

APDEX_THRESHOLDS = {"mode": "absolute", "steps": [
    {"color": "red", "value": None}, {"color": "orange", "value": 0.7}, {"color": "green", "value": 0.85}]}
ERROR_THRESHOLDS = {"mode": "absolute", "steps": [
    {"color": "green", "value": None}, {"color": "orange", "value": 0.01}, {"color": "red", "value": 0.05}]}


class Q:
    """PromQL fragments for one source and one label selector."""

    def __init__(self, source, sel):
        self.source = source
        if source == "beyla":
            self.count = f"http_server_request_duration_seconds_count{{{sel}}}"
            self.bucket = "http_server_request_duration_seconds_bucket{%s}" % sel
            self.errors = f'http_server_request_duration_seconds_count{{{sel},http_response_status_code=~"5.."}}'
            self.client_errors = f'http_server_request_duration_seconds_count{{{sel},http_response_status_code=~"4.."}}'
            self.route = "http_route"
            self.method = "http_request_method"
        else:
            base = f'{sel},span_kind="SPAN_KIND_SERVER"'
            self.count = f"traces_spanmetrics_calls_total{{{base}}}"
            self.bucket = "traces_spanmetrics_latency_bucket{%s}" % base
            self.errors = f'traces_spanmetrics_calls_total{{{base},status_code="STATUS_CODE_ERROR"}}'
            self.client_errors = None
            self.route = "span_name"
            self.method = None
        self.t, self.f, _ = APDEX[source]

    def b(self, le):
        return self.bucket[:-1] + f',le="{le}"}}'

    def rate(self, m, by=""):
        g = f" by ({by})" if by else ""
        return f"sum{g} (rate({m}[5m]))"

    def apdex(self, by=""):
        return (f"((({self.rate(self.b(self.t), by)}) + ({self.rate(self.b(self.f), by)})) / 2)"
                f" / {self.rate(self.count, by)}")

    def err_ratio(self, by=""):
        return f"(({self.rate(self.errors, by)}) or ({self.rate(self.count, by)} * 0)) / {self.rate(self.count, by)}"

    def quantile(self, p, by=""):
        extra = f"{by}, " if by else ""
        return f"histogram_quantile({p}, sum by ({extra}le) (rate({self.bucket}[5m])))"


def target(expr, ref="A", legend=None, table=False):
    t = {"refId": ref, "expr": expr, "datasource": DS}
    if legend:
        t["legendFormat"] = legend
    if table:
        t["format"] = "table"
        t["instant"] = True
    return t


class Board:
    def __init__(self):
        self.panels = []

    def add(self, typ, title, pos, targets, unit=None, desc=None, **kw):
        p = {"id": len(self.panels) + 1, "type": typ, "title": title, "datasource": DS,
             "gridPos": dict(zip("xywh", pos)), "targets": targets,
             "fieldConfig": {"defaults": {"unit": unit} if unit else {}, "overrides": []}}
        if typ == "row":
            p = {"id": len(self.panels) + 1, "type": "row", "title": title, "gridPos": dict(zip("xywh", pos)),
                 "collapsed": False, "panels": []}
        if typ == "stat":
            p["options"] = {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "value", "graphMode": "area"}
        if desc:
            p["description"] = desc
        p.update(kw)
        self.panels.append(p)
        return p


def app_board(app):
    src = app["source"]
    sel = f'service_name="{app["service"]}"' if src == "beyla" else f'service="{app["service"]}"'
    q = Q(src, sel)
    t_label = APDEX[src][2]
    bd = Board()
    y = 0
    p = bd.add("stat", f"Apdex (T = {t_label})", (0, y, 4, 5), [target(q.apdex())], "percentunit",
               "Satisfied requests plus half of tolerating (up to 4T), over all requests.")
    p["fieldConfig"]["defaults"].update({"thresholds": APDEX_THRESHOLDS, "min": 0, "max": 1})
    bd.add("stat", "Throughput (rpm)", (4, y, 4, 5), [target(f"{q.rate(q.count)} * 60")], "short")
    p = bd.add("stat", "Error rate (5xx)" if src == "beyla" else "Error rate (error spans)", (8, y, 4, 5),
               [target(q.err_ratio())], "percentunit")
    p["fieldConfig"]["defaults"]["thresholds"] = ERROR_THRESHOLDS
    bd.add("stat", "Response time p50", (12, y, 4, 5), [target(q.quantile(0.5))], "s")
    bd.add("stat", "Response time p95", (16, y, 4, 5), [target(q.quantile(0.95))], "s")
    bd.add("stat", "Response time p99", (20, y, 4, 5), [target(q.quantile(0.99))], "s")
    y += 5
    bd.add("timeseries", "Web transactions time (p50 / p95 / p99)", (0, y, 12, 8),
           [target(q.quantile(0.5), "A", "p50"), target(q.quantile(0.95), "B", "p95"), target(q.quantile(0.99), "C", "p99")], "s")
    bd.add("timeseries", "Throughput by endpoint (req/s)", (12, y, 12, 8),
           [target(f"topk(10, {q.rate(q.count, q.route)})", legend="{{%s}}" % q.route)], "reqps")
    y += 8
    p = bd.add("timeseries", "Apdex over time", (0, y, 12, 8), [target(q.apdex(), legend="apdex")], "percentunit")
    p["fieldConfig"]["defaults"].update({"min": 0, "max": 1})
    err_targets = [target(q.err_ratio(), "A", "5xx" if src == "beyla" else "errors")]
    if q.client_errors:
        err_targets.append(target(
            f"(({q.rate(q.client_errors)}) or ({q.rate(q.count)} * 0)) / {q.rate(q.count)}", "B", "4xx"))
    bd.add("timeseries", "Error rate (share of requests)", (12, y, 12, 8), err_targets, "percentunit")
    y += 8
    by = f"{q.method}, {q.route}" if q.method else q.route
    tbl = [target(f"{q.rate(q.count, by)} * 60", "A", table=True),
           target(q.quantile(0.95, by), "B", table=True),
           target(q.err_ratio(by), "C", table=True)]
    rename = {q.route: "Endpoint", "Value #A": "rpm", "Value #B": "p95", "Value #C": "error rate"}
    if q.method:
        rename[q.method] = "Method"
    p = bd.add("table", "Transactions by endpoint", (0, y, 24, 10), tbl,
               transformations=[{"id": "merge", "options": {}},
                                {"id": "organize", "options": {"excludeByName": {"Time": True}, "renameByName": rename}}],
               options={"sortBy": [{"displayName": "rpm", "desc": True}]})
    p["fieldConfig"]["overrides"] = [
        {"matcher": {"id": "byName", "options": "p95"}, "properties": [{"id": "unit", "value": "s"}]},
        {"matcher": {"id": "byName", "options": "error rate"}, "properties": [{"id": "unit", "value": "percentunit"}]},
        {"matcher": {"id": "byName", "options": "rpm"}, "properties": [{"id": "decimals", "value": 2}]}]
    y += 10
    if src == "beyla":
        bd.add("row", "Dependencies", (0, y, 24, 1), [])
        y += 1
        s = f'service_name="{app["service"]}"'
        bd.add("timeseries", "Outbound HTTP p95 by destination", (0, y, 12, 8),
               [target(f"histogram_quantile(0.95, sum by (server_address, le) (rate(http_client_request_duration_seconds_bucket{{{s}}}[5m])))",
                       legend="{{server_address}}")], "s")
        bd.add("timeseries", "Database calls p95 by operation", (12, y, 12, 8),
               [target(f"histogram_quantile(0.95, sum by (db_operation_name, le) (rate(db_client_operation_duration_seconds_bucket{{{s}}}[5m])))",
                       legend="{{db_operation_name}}")], "s")
        y += 8
    bd.add("row", "Container", (0, y, 24, 1), [])
    y += 1
    csel = f'namespace="{app["namespace"]}",container!="",container!="POD"'
    if app["container"]:
        csel = f'namespace="{app["namespace"]}",container="{app["container"]}"'
    bd.add("timeseries", "CPU (cores)", (0, y, 8, 8),
           [target(f"sum by (pod) (rate(container_cpu_usage_seconds_total{{{csel}}}[5m]))", legend="{{pod}}")], "short")
    bd.add("timeseries", "Memory (working set)", (8, y, 8, 8),
           [target(f"sum by (pod) (container_memory_working_set_bytes{{{csel}}})", legend="{{pod}}")], "bytes")
    bd.add("timeseries", "Restarts (last 1h)", (16, y, 8, 8),
           [target(f'sum by (pod) (increase(kube_pod_container_status_restarts_total{{namespace="{app["namespace"]}"}}[1h]))',
                   legend="{{pod}}")], "short")
    source_note = ("Beyla eBPF metrics: every request counted, no app changes."
                   if src == "beyla" else "Tempo span metrics from the app's own OpenTelemetry traces.")
    return {
        "title": f"{app['title']} APM", "uid": f"apm-{app['slug']}", "tags": ["apm", app["slug"]],
        "timezone": "browser", "schemaVersion": 39, "refresh": "30s", "time": {"from": "now-6h", "to": "now"},
        "description": f"New Relic-style APM for {app['title']}. {source_note} Generated by gen_apm.py.",
        "links": [{"title": "Environment APM", "type": "link", "url": "/d/apm-environment"},
                  {"title": "Traces APM (service map)", "type": "link", "url": "/d/traces-apm"}],
        "panels": bd.panels,
    }


def env_board():
    """Consolidated view: every app on one page, Jellyfin and Keycloak included."""
    # Every traced service at once (RomM as "api", Keycloak, and whatever CHG0030481
    # adds), grouped by the span-metrics "service" label and renamed to service_name
    # so it joins the Jellyfin rows below. The Beyla union was removed with Beyla.
    tr = Q("traces", 'service=~".+"')
    jf_sel = 'job="jellyfin"'
    jf_count = f"http_request_duration_seconds_count{{{jf_sel}}}"
    jf_bucket = "http_request_duration_seconds_bucket{%s}" % jf_sel
    jt, jfr, _ = APDEX["jellyfin"]

    def jf_rate(m):
        return f"sum(rate({m}[5m]))"

    def lr(expr, name):
        return f'label_replace({expr}, "service_name", "{name}", "", "")'

    jf_apdex = (f'((sum(rate({jf_bucket[:-1]},le="{jt}"}}[5m])) + sum(rate({jf_bucket[:-1]},le="{jfr}"}}[5m]))) / 2)'
                f" / {jf_rate(jf_count)}")
    jf_err = (f'((sum(rate(http_request_duration_seconds_count{{{jf_sel},code=~"5.."}}[5m]))) or ({jf_rate(jf_count)} * 0))'
              f" / {jf_rate(jf_count)}")
    jf_p95 = f"histogram_quantile(0.95, sum by (le) (rate({jf_bucket}[5m])))"

    def by_service(expr):
        return f'label_replace({expr}, "service_name", "$1", "service", "(.*)")'

    def union(tr_expr, jf_expr):
        return f"{by_service(tr_expr)} or {lr(jf_expr, 'jellyfin')}"

    apdex_by = union(tr.apdex("service"), jf_apdex)
    rpm_by = union(f"{tr.rate(tr.count, 'service')} * 60", f"{jf_rate(jf_count)} * 60")
    err_by = union(tr.err_ratio("service"), jf_err)
    p95_by = union(tr.quantile(0.95, "service"), jf_p95)

    bd = Board()
    p = bd.add("stat", "Environment Apdex (request-weighted)", (0, 0, 6, 5),
               [target(f"sum(({apdex_by}) * on (service_name) ({rpm_by})) / sum({rpm_by})")],
               "percentunit", "Each app's Apdex weighted by its traffic. Traced apps T = 0.512s, Jellyfin 0.256s.")
    p["fieldConfig"]["defaults"].update({"thresholds": APDEX_THRESHOLDS, "min": 0, "max": 1})
    bd.add("stat", "Total throughput (rpm)", (6, 0, 6, 5), [target(f"sum({rpm_by})")], "short")
    p = bd.add("stat", "Environment error rate", (12, 0, 6, 5),
               [target(f"sum(({err_by}) * on (service_name) ({rpm_by})) / sum({rpm_by})")], "percentunit")
    p["fieldConfig"]["defaults"]["thresholds"] = ERROR_THRESHOLDS
    p = bd.add("stat", "Apps below Apdex 0.85", (18, 0, 6, 5), [target(f"count(({apdex_by}) < 0.85) or vector(0)")], "short")
    p["fieldConfig"]["defaults"]["thresholds"] = {"mode": "absolute", "steps": [
        {"color": "green", "value": None}, {"color": "orange", "value": 1}]}
    tbl = [target(apdex_by, "A", table=True), target(rpm_by, "B", table=True),
           target(err_by, "C", table=True), target(p95_by, "D", table=True)]
    p = bd.add("table", "Apps", (0, 5, 24, 10), tbl,
               transformations=[{"id": "merge", "options": {}},
                                {"id": "organize", "options": {"excludeByName": {"Time": True}, "renameByName": {
                                    "service_name": "App", "Value #A": "Apdex", "Value #B": "rpm",
                                    "Value #C": "error rate", "Value #D": "p95"}}}],
               options={"sortBy": [{"displayName": "Apdex", "desc": False}]})
    links = [{"title": f"{a['title']} APM", "url": f"/d/apm-{a['slug']}?${{__url_time_range}}"} for a in APPS]
    links.append({"title": "Jellyfin APM", "url": "/d/jellyfin-apm?${__url_time_range}"})
    p["fieldConfig"]["overrides"] = [
        {"matcher": {"id": "byName", "options": "Apdex"}, "properties": [
            {"id": "unit", "value": "percentunit"}, {"id": "thresholds", "value": APDEX_THRESHOLDS},
            {"id": "custom.cellOptions", "value": {"type": "color-background"}}]},
        {"matcher": {"id": "byName", "options": "error rate"}, "properties": [{"id": "unit", "value": "percentunit"}]},
        {"matcher": {"id": "byName", "options": "p95"}, "properties": [{"id": "unit", "value": "s"}]},
        {"matcher": {"id": "byName", "options": "rpm"}, "properties": [{"id": "decimals", "value": 2}]},
        {"matcher": {"id": "byName", "options": "App"}, "properties": [{"id": "links", "value": [
            {"title": "Open ${__value.text} APM", "url": "/d/apm-${__value.text}?${__url_time_range}"}]}]}]
    p = bd.add("timeseries", "Apdex by app", (0, 15, 12, 9), [target(apdex_by, legend="{{service_name}}")], "percentunit")
    p["fieldConfig"]["defaults"].update({"min": 0, "max": 1})
    bd.add("timeseries", "Throughput by app (rpm)", (12, 15, 12, 9), [target(rpm_by, legend="{{service_name}}")], "short")
    bd.add("timeseries", "p95 by app", (0, 24, 12, 9), [target(p95_by, legend="{{service_name}}")], "s")
    bd.add("timeseries", "Error rate by app", (12, 24, 12, 9), [target(err_by, legend="{{service_name}}")], "percentunit")
    return {
        "title": "Environment APM", "uid": "apm-environment", "tags": ["apm"], "timezone": "browser",
        "schemaVersion": 39, "refresh": "30s", "time": {"from": "now-6h", "to": "now"},
        "description": "Every app's Apdex, throughput, errors and p95 on one page. Click an app to open its APM. Generated by gen_apm.py.",
        "links": links + [{"title": "Traces APM (service map)", "url": "/d/traces-apm"}],
        "panels": bd.panels,
    }


if __name__ == "__main__":
    for a in APPS:
        with open(f"apm-{a['slug']}.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump(app_board(a), fh, indent=2)
            fh.write("\n")
    with open("apm-environment.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(env_board(), fh, indent=2)
        fh.write("\n")
    print("wrote", len(APPS) + 1, "dashboards")
