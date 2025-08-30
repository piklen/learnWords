#!/usr/bin/env python3
"""
数据库初始化脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.database import engine, SessionLocal
from app.models import Base, User
from app.core.security import get_password_hash

def init_database():
    """初始化数据库"""
    print("🗄️  创建数据库表...")
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建完成")
    
    # 创建管理员用户
    print("👤 创建管理员用户...")
    db = SessionLocal()
    
    try:
        # 检查是否已存在管理员
        admin_user = db.query(User).filter(User.email == "admin@lessonplanner.com").first()
        
        if not admin_user:
            admin_user = User(
                email="admin@lessonplanner.com",
                username="admin",
                hashed_password=get_password_hash("admin123"),
                full_name="系统管理员",
                is_active=True,
                is_verified=True
            )
            
            db.add(admin_user)
            db.commit()
            print("✅ 管理员用户创建完成")
            print("   邮箱: admin@lessonplanner.com")
            print("   密码: admin123")
        else:
            print("ℹ️  管理员用户已存在")
            
    except Exception as e:
        print(f"❌ 创建管理员用户失败: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """主函数"""
    print("🚀 智能教案生成平台 - 数据库初始化")
    print("=" * 50)
    
    try:
        init_database()
        print("\n🎉 数据库初始化完成！")
        print("\n💡 下一步:")
        print("   1. 启动应用: ./start.sh")
        print("   2. 访问API文档: http://localhost:8000/api/docs")
        print("   3. 使用管理员账户登录")
        
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
