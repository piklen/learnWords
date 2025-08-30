import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any
import logging
from urllib.parse import urljoin
import os
from io import BytesIO

from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    """统一存储服务，支持Cloudflare R2、AWS S3和本地存储"""
    
    def __init__(self):
        self.storage_backend = settings.storage_backend
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化存储客户端"""
        if self.storage_backend == "r2":
            self._initialize_r2_client()
        elif self.storage_backend == "s3":
            self._initialize_s3_client()
        elif self.storage_backend == "local":
            self._ensure_local_directory()
        else:
            raise ValueError(f"不支持的存储后端: {self.storage_backend}")
    
    def _initialize_r2_client(self):
        """初始化Cloudflare R2客户端"""
        if not all([settings.r2_access_key_id, settings.r2_secret_access_key, 
                   settings.r2_account_id, settings.r2_bucket_name]):
            raise ValueError("Cloudflare R2配置不完整")
        
        endpoint_url = settings.r2_endpoint_url or f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"
        
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            endpoint_url=endpoint_url,
            region_name='auto'  # R2使用'auto'作为region
        )
        self.bucket_name = settings.r2_bucket_name
        logger.info(f"Cloudflare R2客户端初始化成功，存储桶: {self.bucket_name}")
    
    def _initialize_s3_client(self):
        """初始化AWS S3客户端"""
        if not all([settings.aws_access_key_id, settings.aws_secret_access_key, 
                   settings.aws_s3_bucket]):
            raise ValueError("AWS S3配置不完整")
        
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        self.bucket_name = settings.aws_s3_bucket
        logger.info(f"AWS S3客户端初始化成功，存储桶: {self.bucket_name}")
    
    def _ensure_local_directory(self):
        """确保本地存储目录存在"""
        self.local_storage_path = "uploads"
        os.makedirs(self.local_storage_path, exist_ok=True)
        logger.info(f"本地存储目录: {self.local_storage_path}")
    
    async def upload_file(self, file_content: bytes, key: str, content_type: str = None) -> Dict[str, Any]:
        """
        上传文件到存储服务
        
        Args:
            file_content: 文件内容（字节）
            key: 文件键名/路径
            content_type: 文件MIME类型
            
        Returns:
            Dict包含上传结果信息
        """
        try:
            if self.storage_backend == "local":
                return await self._upload_local(file_content, key)
            else:
                return await self._upload_cloud(file_content, key, content_type)
        except Exception as e:
            logger.error(f"文件上传失败 {key}: {str(e)}")
            raise
    
    async def _upload_local(self, file_content: bytes, key: str) -> Dict[str, Any]:
        """上传到本地存储"""
        file_path = os.path.join(self.local_storage_path, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return {
            "success": True,
            "key": key,
            "url": f"/uploads/{key}",
            "size": len(file_content),
            "storage_backend": "local"
        }
    
    async def _upload_cloud(self, file_content: bytes, key: str, content_type: str = None) -> Dict[str, Any]:
        """上传到云存储（R2或S3）"""
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        self.client.upload_fileobj(
            BytesIO(file_content),
            self.bucket_name,
            key,
            ExtraArgs=extra_args
        )
        
        # 生成公开访问URL
        url = self._generate_public_url(key)
        
        return {
            "success": True,
            "key": key,
            "url": url,
            "size": len(file_content),
            "storage_backend": self.storage_backend
        }
    
    def _generate_public_url(self, key: str) -> str:
        """生成公开访问URL"""
        if self.storage_backend == "r2" and settings.r2_public_domain:
            # 使用自定义域名
            return f"https://{settings.r2_public_domain}/{key}"
        elif self.storage_backend == "r2":
            # 使用R2的默认公开URL格式
            return f"https://{settings.r2_bucket_name}.{settings.r2_account_id}.r2.cloudflarestorage.com/{key}"
        elif self.storage_backend == "s3":
            # 使用S3的默认公开URL格式
            return f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"
        else:
            return f"/uploads/{key}"
    
    async def delete_file(self, key: str) -> bool:
        """
        删除文件
        
        Args:
            key: 文件键名/路径
            
        Returns:
            删除是否成功
        """
        try:
            if self.storage_backend == "local":
                file_path = os.path.join(self.local_storage_path, key)
                if os.path.exists(file_path):
                    os.remove(file_path)
                return True
            else:
                self.client.delete_object(Bucket=self.bucket_name, Key=key)
                return True
        except Exception as e:
            logger.error(f"文件删除失败 {key}: {str(e)}")
            return False
    
    async def get_file(self, key: str) -> Optional[bytes]:
        """
        获取文件内容
        
        Args:
            key: 文件键名/路径
            
        Returns:
            文件内容（字节）或None
        """
        try:
            if self.storage_backend == "local":
                file_path = os.path.join(self.local_storage_path, key)
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        return f.read()
                return None
            else:
                response = self.client.get_object(Bucket=self.bucket_name, Key=key)
                return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"文件不存在: {key}")
                return None
            logger.error(f"获取文件失败 {key}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取文件失败 {key}: {str(e)}")
            return None
    
    async def file_exists(self, key: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            key: 文件键名/路径
            
        Returns:
            文件是否存在
        """
        try:
            if self.storage_backend == "local":
                file_path = os.path.join(self.local_storage_path, key)
                return os.path.exists(file_path)
            else:
                self.client.head_object(Bucket=self.bucket_name, Key=key)
                return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"检查文件存在性失败 {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"检查文件存在性失败 {key}: {str(e)}")
            return False
    
    async def generate_presigned_url(self, key: str, expiration: int = 3600, method: str = 'GET') -> Optional[str]:
        """
        生成预签名URL（用于直接上传或下载）
        
        Args:
            key: 文件键名/路径
            expiration: URL过期时间（秒）
            method: HTTP方法（GET或PUT）
            
        Returns:
            预签名URL或None
        """
        if self.storage_backend == "local":
            # 本地存储不支持预签名URL
            return None
        
        try:
            if method.upper() == 'PUT':
                url = self.client.generate_presigned_url(
                    'put_object',
                    Params={'Bucket': self.bucket_name, 'Key': key},
                    ExpiresIn=expiration
                )
            else:
                url = self.client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': key},
                    ExpiresIn=expiration
                )
            return url
        except Exception as e:
            logger.error(f"生成预签名URL失败 {key}: {str(e)}")
            return None


# 全局存储服务实例
storage_service = StorageService()
