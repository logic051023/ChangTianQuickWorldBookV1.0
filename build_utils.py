#!/usr/bin/env python3
"""
构建工具集 - 修复AIDL问题和构建配置
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


class BuildError(Exception):
    """构建错误异常"""
    pass


class BuildUtils:
    """构建工具类"""
    
    def __init__(self):
        self.android_home = Path(os.environ.get('ANDROID_HOME', '/home/runner/android-sdk'))
        self.project_root = Path(".")
        
    def check_aidl_tool(self):
        """检查AIDL工具"""
        print("=== 检查AIDL工具 ===")
        
        # 在多个可能的位置查找AIDL
        possible_paths = [
            self.android_home / "build-tools" / "34.0.0" / "aidl",
            self.android_home / "build-tools" / "33.0.0" / "aidl",
            self.android_home / "build-tools" / "30.0.3" / "aidl",
        ]
        
        aidl_found = None
        for aidl_path in possible_paths:
            if aidl_path.exists():
                aidl_found = aidl_path
                print(f"✓ 找到AIDL工具: {aidl_path}")
                break
        
        if not aidl_found:
            print("✗ 未找到AIDL工具，搜索整个SDK...")
            result = subprocess.run(
                f"find {self.android_home} -name 'aidl' -type f 2>/dev/null",
                shell=True, capture_output=True, text=True
            )
            if result.stdout:
                print("找到的AIDL位置:")
                print(result.stdout)
            else:
                print("未找到任何AIDL工具")
            
            raise BuildError("AIDL工具未找到，请确保Android构建工具已正确安装")
        
        return aidl_found
    
    def validate_buildozer_config(self):
        """验证Buildozer配置"""
        print("=== 验证Buildozer配置 ===")
        
        try:
            # 检查buildozer.spec语法
            result = subprocess.run(
                ["buildozer", "android", "checkconfig"],
                capture_output=True, text=True, cwd=self.project_root
            )
            
            if result.returncode != 0:
                print("Buildozer配置检查失败:")
                print(result.stdout)
                print(result.stderr)
                raise BuildError("Buildozer配置验证失败")
            
            print("✓ Buildozer配置验证通过")
            
        except Exception as e:
            raise BuildError(f"配置验证失败: {e}")
    
    def setup_build_environment(self):
        """设置构建环境"""
        print("=== 设置构建环境 ===")
        
        try:
            # 检查AIDL工具
            self.check_aidl_tool()
            
            # 验证配置
            self.validate_buildozer_config()
            
            # 确保必要的目录存在
            (self.project_root / "bin").mkdir(exist_ok=True)
            (self.project_root / ".buildozer").mkdir(exist_ok=True)
            
            print("✓ 构建环境设置完成")
            
        except Exception as e:
            raise BuildError(f"环境设置失败: {e}")
    
    def check_build_result(self):
        """检查构建结果"""
        try:
            print("=== 检查构建结果 ===")
            
            bin_dir = self.project_root / "bin"
            if not bin_dir.exists():
                raise BuildError("构建目录不存在")
            
            apk_files = list(bin_dir.glob("*.apk"))
            if not apk_files:
                # 尝试在项目根目录查找
                apk_files = list(self.project_root.glob("*.apk"))
                
            if not apk_files:
                raise BuildError("未找到APK文件")
            
            for apk in apk_files:
                size_mb = apk.stat().st_size / (1024 * 1024)
                print(f"✓ 找到APK: {apk.name} ({size_mb:.1f} MB)")
            
            print("✓ 构建成功!")
            
        except BuildError as e:
            print(f"✗ 构建失败: {e}")
            
            # 分析构建日志
            self._analyze_build_log()
            sys.exit(1)
    
    def _analyze_build_log(self):
        """分析构建日志"""
        build_log = self.project_root / "build.log"
        if build_log.exists():
            print("=== 构建日志分析 ===")
            
            with open(build_log, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
                # 查找错误和警告
                errors = []
                warnings = []
                
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    if 'error' in line_lower:
                        errors.append((i+1, line.strip()))
                    elif 'warning' in line_lower:
                        warnings.append((i+1, line.strip()))
                    elif 'failed' in line_lower:
                        errors.append((i+1, line.strip()))
                
                if errors:
                    print("关键错误:")
                    for line_num, error in errors[-20:]:  # 最后20个错误
                        print(f"  第{line_num}行: {error}")
                
                if warnings:
                    print("警告信息:")
                    for line_num, warning in warnings[-10:]:
                        print(f"  第{line_num}行: {warning}")
                
                # 显示日志最后部分
                print("构建日志最后50行:")
                for line in lines[-50:]:
                    print(line.rstrip())
        else:
            print("无构建日志文件")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python build_utils.py [setup-environment|check-build-result|check-aidl]")
        sys.exit(1)
    
    command = sys.argv[1]
    utils = BuildUtils()
    
    try:
        if command == "setup-environment":
            utils.setup_build_environment()
        elif command == "check-build-result":
            utils.check_build_result()
        elif command == "check-aidl":
            utils.check_aidl_tool()
        else:
            print(f"未知命令: {command}")
            sys.exit(1)
    except BuildError as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
