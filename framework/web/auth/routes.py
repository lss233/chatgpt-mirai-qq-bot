from quart import Blueprint, request, jsonify
from datetime import timedelta

from .models import LoginRequest, ChangePasswordRequest, TokenResponse
from .utils import (
    is_first_time, save_password, verify_saved_password,
    create_access_token
)
from .middleware import require_auth

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
async def login():
    data = await request.get_json()
    login_data = LoginRequest(**data)
    
    if is_first_time():
        save_password(login_data.password)
        token = create_access_token(timedelta(days=1))
        return TokenResponse(access_token=token).dict()
    
    if not verify_saved_password(login_data.password):
        return jsonify({"error": "Invalid password"}), 401
    
    token = create_access_token(timedelta(days=1))
    return TokenResponse(access_token=token).dict()

@auth_bp.route('/change-password', methods=['POST'])
@require_auth
async def change_password():
    data = await request.get_json()
    password_data = ChangePasswordRequest(**data)
    
    if not verify_saved_password(password_data.old_password):
        return jsonify({"error": "Invalid old password"}), 401
    
    save_password(password_data.new_password)
    return jsonify({"message": "Password changed successfully"}) 