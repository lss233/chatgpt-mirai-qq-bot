import secrets
from datetime import timedelta

from quart import Blueprint, g, jsonify, request

from kirara_ai.config.config_loader import CONFIG_FILE, ConfigLoader
from kirara_ai.config.global_config import GlobalConfig

from .middleware import require_auth
from .models import ChangePasswordRequest, LoginRequest, TokenResponse
from .services import AuthService

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
async def login():
    data = await request.get_json()
    login_data = LoginRequest(**data)

    auth_service: AuthService = g.container.resolve(AuthService)

    if auth_service.is_first_time():
        auth_service.save_password(login_data.password)
        token = auth_service.create_access_token(timedelta(days=1))
        return TokenResponse(access_token=token).model_dump()

    if not auth_service.verify_password(login_data.password):
        return jsonify({"error": "Invalid password"}), 401

    token = auth_service.create_access_token(timedelta(days=1))
    return TokenResponse(access_token=token).model_dump()


@auth_bp.route("/change-password", methods=["POST"])
@require_auth
async def change_password():
    data = await request.get_json()
    password_data = ChangePasswordRequest(**data)

    auth_service: AuthService = g.container.resolve(AuthService)

    if not auth_service.verify_password(password_data.old_password):
        return jsonify({"error": "Invalid old password"})

    auth_service.save_password(password_data.new_password)
    # 重新设置一个 secret_key，让所有的 token 失效
    config: GlobalConfig = g.container.resolve(GlobalConfig)
    config.web.secret_key = secrets.token_hex(32)
    ConfigLoader.save_config_with_backup(CONFIG_FILE, config)
    g.container.resolve(AuthService).secret_key = config.web.secret_key
    
    return jsonify({"message": "Password changed successfully"})


@auth_bp.route("/check-first-time", methods=["GET"])
async def check_first_time():
    auth_service: AuthService = g.container.resolve(AuthService)
    return jsonify({"is_first_time": auth_service.is_first_time()})
