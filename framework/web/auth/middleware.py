from functools import wraps
from quart import request, jsonify
from .utils import verify_token, is_first_time

def require_auth(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        # 如果是首次访问，跳过认证
        if is_first_time():
            return await f(*args, **kwargs)
        
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No authorization header"}), 401
        
        try:
            token_type, token = auth_header.split()
            if token_type.lower() != 'bearer':
                return jsonify({"error": "Invalid token type"}), 401
            
            if not verify_token(token):
                return jsonify({"error": "Invalid token"}), 401
            
            return await f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": str(e)}), 401
    
    return decorated_function 