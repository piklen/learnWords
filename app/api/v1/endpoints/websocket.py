from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.security import HTTPBearer
from typing import Dict, List, Optional
import json
import logging
from datetime import datetime
from app.core.config import settings
from app.core.security import verify_token
from app.core.cache import cache

logger = logging.getLogger(__name__)
router = APIRouter()

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        
        # 存储连接
        connection_id = f"{user_id}_{datetime.now().timestamp()}"
        self.active_connections[connection_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)
        
        # 发送连接成功消息
        await self.send_personal_message(
            {"type": "connection", "status": "connected", "connection_id": connection_id},
            websocket
        )
        
        # 更新用户在线状态
        await self.update_user_status(user_id, "online")
        
        logger.info(f"用户 {user_id} WebSocket连接建立，连接ID: {connection_id}")
        return connection_id
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """断开WebSocket连接"""
        # 从活跃连接中移除
        connection_id = None
        for cid, ws in self.active_connections.items():
            if ws == websocket:
                connection_id = cid
                break
        
        if connection_id:
            del self.active_connections[connection_id]
        
        # 从用户连接列表中移除
        if user_id in self.user_connections:
            self.user_connections[user_id] = [ws for ws in self.user_connections[user_id] if ws != websocket]
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
                # 更新用户离线状态
                self.update_user_status(user_id, "offline")
        
        logger.info(f"用户 {user_id} WebSocket连接断开")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"发送个人消息失败: {e}")
    
    async def send_to_user(self, user_id: str, message: dict):
        """发送消息给指定用户的所有连接"""
        if user_id in self.user_connections:
            for websocket in self.user_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                except Exception as e:
                    logger.error(f"发送消息给用户 {user_id} 失败: {e}")
    
    async def broadcast(self, message: dict, exclude_user: Optional[str] = None):
        """广播消息给所有用户"""
        for user_id, connections in self.user_connections.items():
            if exclude_user and user_id == exclude_user:
                continue
            
            for websocket in connections:
                try:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                except Exception as e:
                    logger.error(f"广播消息给用户 {user_id} 失败: {e}")
    
    async def update_user_status(self, user_id: str, status: str):
        """更新用户在线状态"""
        status_data = {
            "type": "user_status",
            "user_id": user_id,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        # 缓存用户状态
        cache.set(f"user:status:{user_id}", status_data, ttl=300)
        
        # 广播状态更新
        await self.broadcast(status_data, exclude_user=user_id)
    
    def get_online_users(self) -> List[str]:
        """获取在线用户列表"""
        return list(self.user_connections.keys())
    
    def get_user_connection_count(self, user_id: str) -> int:
        """获取用户的连接数量"""
        if user_id in self.user_connections:
            return len(self.user_connections[user_id])
        return 0

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket连接端点"""
    try:
        # 建立连接
        connection_id = await manager.connect(websocket, user_id)
        
        # 发送系统信息
        await manager.send_personal_message({
            "type": "system_info",
            "message": "WebSocket连接已建立",
            "user_id": user_id,
            "connection_id": connection_id,
            "timestamp": datetime.now().isoformat()
        }, websocket)
        
        # 发送在线用户列表
        online_users = manager.get_online_users()
        await manager.send_personal_message({
            "type": "online_users",
            "users": online_users,
            "count": len(online_users)
        }, websocket)
        
        # 消息处理循环
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # 处理不同类型的消息
                await handle_message(websocket, user_id, message_data)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "无效的JSON格式"
                }, websocket)
            except Exception as e:
                logger.error(f"处理WebSocket消息失败: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"消息处理失败: {str(e)}"
                }, websocket)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        manager.disconnect(websocket, user_id)

async def handle_message(websocket: WebSocket, user_id: str, message_data: dict):
    """处理WebSocket消息"""
    message_type = message_data.get("type")
    
    if message_type == "ping":
        # 响应ping
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, websocket)
    
    elif message_type == "chat":
        # 处理聊天消息
        chat_message = {
            "type": "chat",
            "user_id": user_id,
            "message": message_data.get("message", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        # 广播给所有用户
        await manager.broadcast(chat_message)
    
    elif message_type == "notification":
        # 处理通知消息
        target_user = message_data.get("target_user")
        if target_user:
            await manager.send_to_user(target_user, {
                "type": "notification",
                "from_user": user_id,
                "message": message_data.get("message", ""),
                "timestamp": datetime.now().isoformat()
            })
    
    elif message_type == "file_progress":
        # 处理文件上传进度
        progress_data = {
            "type": "file_progress",
            "user_id": user_id,
            "file_id": message_data.get("file_id"),
            "progress": message_data.get("progress", 0),
            "status": message_data.get("status", "uploading"),
            "timestamp": datetime.now().isoformat()
        }
        
        # 发送给用户自己
        await manager.send_personal_message(progress_data, websocket)
    
    elif message_type == "task_status":
        # 处理任务状态更新
        task_data = {
            "type": "task_status",
            "user_id": user_id,
            "task_id": message_data.get("task_id"),
            "status": message_data.get("status", "pending"),
            "progress": message_data.get("progress", 0),
            "message": message_data.get("message", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        # 发送给用户自己
        await manager.send_personal_message(task_data, websocket)
    
    else:
        # 未知消息类型
        await manager.send_personal_message({
            "type": "error",
            "message": f"未知的消息类型: {message_type}"
        }, websocket)

@router.get("/ws/status")
async def get_websocket_status():
    """获取WebSocket状态"""
    return {
        "status": "active",
        "active_connections": len(manager.active_connections),
        "online_users": manager.get_online_users(),
        "user_count": len(manager.user_connections)
    }

@router.get("/ws/users/{user_id}/status")
async def get_user_status(user_id: str):
    """获取用户状态"""
    # 从缓存获取状态
    status_data = cache.get(f"user:status:{user_id}")
    
    if not status_data:
        status_data = {
            "user_id": user_id,
            "status": "offline",
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "user_id": user_id,
        "status": status_data.get("status", "offline"),
        "connection_count": manager.get_user_connection_count(user_id),
        "last_seen": status_data.get("timestamp")
    }
