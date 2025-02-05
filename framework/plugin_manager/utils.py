from importlib.metadata import distribution, PackageNotFoundError
from typing import Optional, Dict, Any

def get_package_metadata(package_name: str) -> Optional[Dict[str, Any]]:
    """获取Python包的元数据
    
    Args:
        package_name: 包名
        
    Returns:
        包含包元数据的字典，如果包不存在则返回None
    """
    try:
        dist = distribution(package_name)
        return {
            'name': dist.metadata['Name'],
            'version': dist.version,
            'description': dist.metadata.get('Summary', ''),
            'author': dist.metadata.get('Author', '')
        }
    except PackageNotFoundError:
        return None 