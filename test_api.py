#!/usr/bin/env python3
"""
智能教案生成平台 API 测试脚本
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    """测试健康检查"""
    print("🔍 测试健康检查...")
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ 健康检查通过")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保服务已启动")
        return False

def test_register():
    """测试用户注册"""
    print("\n👤 测试用户注册...")
    
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "测试用户"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
        if response.status_code == 200:
            print("✅ 用户注册成功")
            user_info = response.json()
            print(f"   用户ID: {user_info['id']}")
            return user_info
        else:
            print(f"❌ 用户注册失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 注册请求异常: {e}")
        return None

def test_login(user_data):
    """测试用户登录"""
    print("\n🔐 测试用户登录...")
    
    login_data = {
        "username": user_data["email"],
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        if response.status_code == 200:
            print("✅ 用户登录成功")
            token_info = response.json()
            print(f"   访问令牌: {token_info['access_token'][:20]}...")
            return token_info["access_token"]
        else:
            print(f"❌ 用户登录失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 登录请求异常: {e}")
        return None

def test_documents(token):
    """测试文档相关API"""
    print("\n📚 测试文档API...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试获取上传URL
    print("   测试获取上传URL...")
    try:
        response = requests.post(
            f"{BASE_URL}/documents/upload-url",
            params={"filename": "test.pdf"},
            headers=headers
        )
        if response.status_code == 200:
            print("✅ 获取上传URL成功")
            upload_info = response.json()
            print(f"   文档ID: {upload_info['document_id']}")
            return upload_info["document_id"]
        else:
            print(f"❌ 获取上传URL失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 获取上传URL异常: {e}")
        return None

def test_lesson_plans(token, document_id):
    """测试教案相关API"""
    print("\n📝 测试教案API...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 测试创建教案
    print("   测试创建教案...")
    lesson_plan_data = {
        "document_id": document_id,
        "grade_level": "高中一年级",
        "subject": "数学",
        "duration_minutes": 45,
        "learning_objectives": "理解函数的基本概念",
        "pedagogical_style": "探究式学习",
        "activities": ["小组讨论", "案例分析"],
        "assessment_methods": ["课堂提问", "作业检查"],
        "differentiation_strategies": "为不同水平学生提供不同难度的练习"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/lesson-plans/",
            json=lesson_plan_data,
            headers=headers
        )
        if response.status_code == 200:
            print("✅ 创建教案成功")
            lesson_plan = response.json()
            print(f"   教案ID: {lesson_plan['id']}")
            return lesson_plan["id"]
        else:
            print(f"❌ 创建教案失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 创建教案异常: {e}")
        return None

def main():
    """主测试函数"""
    print("🚀 开始测试智能教案生成平台 API")
    print("=" * 50)
    
    # 测试健康检查
    if not test_health():
        return
    
    # 测试用户注册
    user_data = test_register()
    if not user_data:
        return
    
    # 测试用户登录
    token = test_login(user_data)
    if not token:
        return
    
    # 测试文档API
    document_id = test_documents(token)
    if not document_id:
        return
    
    # 测试教案API
    lesson_plan_id = test_lesson_plans(token, document_id)
    if not lesson_plan_id:
        return
    
    print("\n" + "=" * 50)
    print("🎉 所有测试通过！")
    print(f"📊 测试结果:")
    print(f"   - 用户ID: {user_data['id']}")
    print(f"   - 文档ID: {document_id}")
    print(f"   - 教案ID: {lesson_plan_id}")
    print("\n💡 提示:")
    print("   - 访问 http://localhost:8000/api/docs 查看完整API文档")
    print("   - 使用获取的token进行后续API调用")

if __name__ == "__main__":
    main()
