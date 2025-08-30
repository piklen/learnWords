#!/usr/bin/env python3
"""
智能教案生成平台 - 增强API测试脚本
"""

import requests
import json
import time
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000/api/v1"

class LessonPlannerTester:
    """教案生成平台测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.token: Optional[str] = None
        self.user_data: Optional[Dict] = None
        self.document_id: Optional[int] = None
        self.lesson_plan_id: Optional[int] = None
    
    def test_health_check(self) -> bool:
        """测试健康检查"""
        print("🔍 测试健康检查...")
        try:
            response = requests.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("✅ 基础健康检查通过")
                
                # 测试详细健康检查
                response = requests.get(f"{BASE_URL}/health/detailed")
                if response.status_code == 200:
                    health_data = response.json()
                    print("✅ 详细健康检查通过")
                    print(f"   数据库状态: {health_data['services']['database']['status']}")
                    print(f"   Redis状态: {health_data['services']['redis']['status']}")
                    return True
                else:
                    print(f"❌ 详细健康检查失败: {response.status_code}")
                    return False
            else:
                print(f"❌ 基础健康检查失败: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ 无法连接到服务器，请确保服务已启动")
            return False
    
    def test_register(self) -> bool:
        """测试用户注册"""
        print("\n👤 测试用户注册...")
        
        self.user_data = {
            "email": f"test{int(time.time())}@example.com",
            "username": f"testuser{int(time.time())}",
            "password": "testpassword123",
            "full_name": "测试用户"
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/register", json=self.user_data)
            if response.status_code == 200:
                print("✅ 用户注册成功")
                user_info = response.json()
                print(f"   用户ID: {user_info['id']}")
                return True
            else:
                print(f"❌ 用户注册失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 注册请求异常: {e}")
            return False
    
    def test_login(self) -> bool:
        """测试用户登录"""
        print("\n🔐 测试用户登录...")
        
        login_data = {
            "username": self.user_data["email"],
            "password": self.user_data["password"]
        }
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", data=login_data)
            if response.status_code == 200:
                print("✅ 用户登录成功")
                token_info = response.json()
                self.token = token_info["access_token"]
                print(f"   访问令牌: {self.token[:20]}...")
                
                # 设置认证头
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                return True
            else:
                print(f"❌ 用户登录失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 登录请求异常: {e}")
            return False
    
    def test_documents(self) -> bool:
        """测试文档相关API"""
        print("\n📚 测试文档API...")
        
        # 测试获取上传URL
        print("   测试获取上传URL...")
        try:
            response = self.session.post(
                f"{BASE_URL}/documents/upload-url",
                params={"filename": "test.pdf"}
            )
            if response.status_code == 200:
                print("✅ 获取上传URL成功")
                upload_info = response.json()
                self.document_id = upload_info["document_id"]
                print(f"   文档ID: {self.document_id}")
                return True
            else:
                print(f"❌ 获取上传URL失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 获取上传URL异常: {e}")
            return False
    
    def test_lesson_plans(self) -> bool:
        """测试教案相关API"""
        print("\n📝 测试教案API...")
        
        if not self.document_id:
            print("❌ 需要先创建文档")
            return False
        
        # 测试创建教案
        print("   测试创建教案...")
        lesson_plan_data = {
            "document_id": self.document_id,
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
            response = self.session.post(
                f"{BASE_URL}/lesson-plans/",
                json=lesson_plan_data
            )
            if response.status_code == 200:
                print("✅ 创建教案成功")
                lesson_plan = response.json()
                self.lesson_plan_id = lesson_plan["id"]
                print(f"   教案ID: {self.lesson_plan_id}")
                return True
            else:
                print(f"❌ 创建教案失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 创建教案异常: {e}")
            return False
    
    def test_admin_endpoints(self) -> bool:
        """测试管理后台API"""
        print("\n👨‍💼 测试管理后台API...")
        
        # 注意：这里需要管理员权限，我们只是测试端点是否存在
        try:
            response = self.session.get(f"{BASE_URL}/admin/dashboard")
            if response.status_code in [200, 401, 403]:  # 成功或权限不足都是正常的
                print("✅ 管理后台端点可访问")
                return True
            else:
                print(f"❌ 管理后台端点异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 管理后台API异常: {e}")
            return False
    
    def test_metrics(self) -> bool:
        """测试指标API"""
        print("\n📊 测试指标API...")
        
        try:
            response = self.session.get(f"{BASE_URL}/health/metrics")
            if response.status_code == 200:
                print("✅ 指标API访问成功")
                metrics = response.json()
                print(f"   调试模式: {metrics['system']['debug_mode']}")
                print(f"   最大文件大小: {metrics['system']['max_file_size'] / (1024*1024):.1f}MB")
                return True
            else:
                print(f"❌ 指标API访问失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 指标API异常: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始测试智能教案生成平台 API")
        print("=" * 60)
        
        tests = [
            ("健康检查", self.test_health_check),
            ("用户注册", self.test_register),
            ("用户登录", self.test_login),
            ("文档API", self.test_documents),
            ("教案API", self.test_lesson_plans),
            ("管理后台", self.test_admin_endpoints),
            ("指标API", self.test_metrics)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    print(f"❌ {test_name}测试失败")
            except Exception as e:
                print(f"❌ {test_name}测试异常: {e}")
        
        print("\n" + "=" * 60)
        print(f"📊 测试结果: {passed}/{total} 通过")
        
        if passed == total:
            print("🎉 所有测试通过！")
            print(f"\n📋 测试详情:")
            print(f"   - 用户ID: {self.user_data['id'] if self.user_data else 'N/A'}")
            print(f"   - 文档ID: {self.document_id}")
            print(f"   - 教案ID: {self.lesson_plan_id}")
        else:
            print("⚠️  部分测试失败，请检查系统状态")
        
        print("\n💡 提示:")
        print("   - 访问 http://localhost:8000/api/docs 查看完整API文档")
        print("   - 使用获取的token进行后续API调用")

def main():
    """主函数"""
    tester = LessonPlannerTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
