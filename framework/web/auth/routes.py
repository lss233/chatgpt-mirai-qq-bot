from quart import Blueprint, request, jsonify, g
from datetime import timedelta

from .models import LoginRequest, ChangePasswordRequest, TokenResponse
from .services import AuthService
from .middleware import require_auth

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
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

@auth_bp.route('/change-password', methods=['POST'])
@require_auth
async def change_password():
    data = await request.get_json()
    password_data = ChangePasswordRequest(**data)
    
    auth_service: AuthService = g.container.resolve(AuthService)
    
    if not auth_service.verify_password(password_data.old_password):
        return jsonify({"error": "Invalid old password"}), 401
    
    auth_service.save_password(password_data.new_password)
    return jsonify({"message": "Password changed successfully"})

@auth_bp.route('/check-first-time', methods=['GET'])
async def check_first_time():
    auth_service: AuthService = g.container.resolve(AuthService)
    return jsonify({"is_first_time": auth_service.is_first_time()}) 