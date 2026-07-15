"""org 등록 API (§10.2 권한 게이트) — GET/POST/DELETE /orgs."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request


def make_orgs_bp(org_service: Any, catalog_service: Any) -> Blueprint:
    bp = Blueprint("orgs", __name__)

    @bp.get("/orgs")
    def list_orgs():
        status = org_service.revalidate_all()
        return jsonify([{
            "name": org.name,
            "url": org.url,
            "kind": org.kind.value,
            "authorized": bool(status.get(org.name, False)),
        } for org in org_service.list_orgs()])

    @bp.post("/orgs")
    def add_org():
        body = request.get_json(silent=True) or {}
        url = str(body.get("url", "")).strip()
        if not url:
            return jsonify({"error": "url이 필요합니다"}), 400
        # 실패 라우팅(§10.2): AuthError → 401(로그인 창 복귀),
        # 멤버십 거부·다른 host(PmError) → 400(사이드바 인라인 표시)
        org = org_service.add(url)
        catalog = catalog_service.scan(org.name)  # 등록 직후 자동 스캔 (§7)
        return jsonify({
            "name": org.name,
            "host": org.host,
            "kind": org.kind.value,
            "plugin_count": len(catalog.get(org.name, [])),
        }), 201

    @bp.delete("/orgs/<name>")
    def remove_org(name: str):
        org_service.remove(name)
        return jsonify({
            "ok": True,
            "note": "설치본은 유지되며 '미등록 org' 그룹으로 계속 "
                    "관리됩니다 (§12.2)",
        })

    return bp
