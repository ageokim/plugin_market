"""로그인 API (§12.6) — POST /login·/logout, GET /session."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request


def make_auth_bp(auth_service: Any, config: Any) -> Blueprint:
    bp = Blueprint("auth", __name__)

    @bp.post("/login")
    def login():
        body = request.get_json(silent=True) or {}
        user_id = str(body.get("id", "")).strip()
        token = str(body.get("token", "")).strip()
        if not user_id or not token:
            return jsonify({"error": "id와 token(PAT)이 필요합니다"}), 400
        result = auth_service.login(user_id, token)  # AuthError → 401 핸들러
        return jsonify({
            "verified": result.verified,  # False = 미검증 세션 (§10.2)
            "login": result.login,
            "first_save": result.first_save,  # 평문 저장 경고 1회 (§8.4)
        })

    @bp.post("/logout")
    def logout():
        auth_service.logout()  # 세션 종료 + credentials.json 삭제 (§12.6)
        return jsonify({"ok": True})

    @bp.get("/session")
    def session():
        saved = auth_service.load_saved()
        return jsonify({
            "logged_in": bool(saved) or auth_service.is_unverified(),
            "unverified": auth_service.is_unverified(),
            "id": auth_service.current_id(),
            "host": config.github_host,
        })

    return bp
