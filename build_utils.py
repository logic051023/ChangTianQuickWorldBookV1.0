#!/usr/bin/env python3
"""
构建工具集 - 修复构建流程问题
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class BuildError(Exception):
    """构建错误异常"""
    pass


class BuildUtils:
    """构建工具类"""
    
    def __init__(self):
        self.project_root = Path(".")
        self.android_home = Path(os.environ.get('ANDROID_HOME', '/home/runner/android-sdk'))
        
    def setup_build_environment(self):
        """设置构建环境"""
        print("=== 设置构建环境 ===")
        
        try:
            # 确保必要的目录存在
            (self.project_root / "bin").mkdir(exist_ok=True)
            
            # 检查Android SDK
            self._check_android_sdk()
            
            # 验证Buildozer配置
            self._validate_buildozer_config()
            
            print("✓ 构建环境设置完成")
            
        except Exception as e:
            raise BuildError(f"环境设置失败: {e}")
    
    def _check_android_sdk(self):
        """检查Android SDK安装"""
        print("=== 检查Android SDK ===")
        
        if not self.android_home.exists():
            raise BuildError(f"Android SDK目录不存在: {self.android_home}")
        
        # 检查构建工具
        build_tools_dirs = list(self.android_home.glob("build-tools/*"))
        if not build_tools_dirs:
            raise BuildError("未找到Android构建工具")
        
        print("找到的构建工具版本:")
        for tool_dir in build_tools_dirs:
            print(f"  - {tool_dir.name}")
            
        # 检查AIDL工具
        aidl_found = False
        for tool_dir in build_tools_dirs:
            aidl_path = tool_dir / "aidl"
            if aidl_path.exists():
                print(f"✓ 找到AIDL工具: {aidl_path}")
                aidl_found = True
                break
        
        if not aidl_found:
            print("⚠ 警告: 未找到AIDL工具，构建可能失败")
    
    def _validate_buildozer_config(self):
        """验证Buildozer配置"""
        print("=== 验证Buildozer配置 ===")
        
        spec_file = self.project_root / "buildozer.spec"
        if not spec_file.exists():
            raise BuildError("buildozer.spec文件不存在")
        
        # 检查关键配置
        with open(spec_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        required_configs = [
            "android.archs",
            "android.api",
            "requirements"
        ]
        
        for config in required_configs:
            if config not in content:
                print(f"⚠ 警告: 配置项 {config} 未找到")
        
        print("✓ Buildozer配置基本验证通过")
    
    def run_build(self):
        """执行构建"""
        print("=== 执行APK构建 ===")
        
        try:
            # 清理之前的构建
            print("清理构建环境...")
            self._run_command("buildozer android clean", check=False)
            
            # 执行构建
            print("开始构建APK...")
            result = self._run_command(
                "buildozer -v android debug", 
                check=False,
                capture=False  # 不捕获输出，直接显示
            )
            
            if result.returncode == 0:
                print("✓ 构建成功完成")
                return True
            else:
                print(f"✗ 构建失败，退出码: {result.returncode}")
                return False
                
        except Exception as e:
            print(f"✗ 构建过程出错: {e}")
            return False
    
    def check_build_result(self):
        """检查构建结果"""
        try:
            print("=== 检查构建结果 ===")
            
            # 在多个可能的位置查找APK
            apk_locations = [
                self.project_root / "bin",
                self.project_root / ".buildozer" / "android" / "platform" / "build" / "dists",
                self.project_root
            ]
            
            apk_files = []
            for location in apk_locations:
                if location.exists():
                    found = list(location.glob("**/*.apk"))
                    apk_files.extend(found)
                    if found:
                        print(f"在 {location} 找到 {len(found)} 个APK文件")
            
            if not apk_files:
                # 检查.buildozer目录结构
                buildozer_dir = self.project_root / ".buildozer"
                if buildozer_dir.exists():
                    print("Buildozer目录结构:")
                    for path in buildozer_dir.glob("**/*"):
                        if path.is_dir():
                            print(f"  DIR: {path.relative_to(self.project_root)}")
                        else:
                            if path.suffix in ['.apk', '.log']:
                                print(f"  FILE: {path.relative_to(self.project_root)}")
                
                raise BuildError("未找到APK文件")
            
            for apk in apk_files:
                size_mb = apk.stat().st_size / (1024 * 1024)
                print(f"✓ 找到APK: {apk.relative_to(self.project_root)} ({size_mb:.1f} MB)")
                
                # 如果是临时位置，复制到bin目录
                if "bin" not in str(apk):
                    bin_dir = self.project_root / "bin"
                    bin_dir.mkdir(exist_ok=True)
                    target_apk = bin_dir / apk.name
                    shutil.copy2(apk, target_apk)
                    print(f"  已复制到: {target_apk}")
            
            print("✓ 构建成功!")
            return True
            
        except BuildError as e:
            print(f"✗ 构建失败: {e}")
            
            # 分析构建日志
            self._analyze_build_log()
            return False
    
    def _analyze_build_log(self):
        """分析构建日志"""
        build_log = self.project_root / "build.log"
        if build_log.exists():
            print("=== 构建日志分析 ===")
            
            with open(build_log, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
                # 查找错误
                error_sections = []
                current_section = []
                
                for line in lines:
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in ['error', 'failed', 'exception']):
                        if current_section:
                            error_sections.append(current_section)
                        current_section = [line]
                    elif current_section and line.strip():
                        current_section.append(line)
                    elif current_section and not line.strip():
                        error_sections.append(current_section)
                        current_section = []
                
                if current_section:
                    error_sections.append(current_section)
                
                if error_sections:
                    print("关键错误信息:")
                    for i, section in enumerate(error_sections[-5:]):  # 最后5个错误段
                        print(f"错误段 {i+1}:")
                        for line in section[:10]:  # 每个段前10行
                            print(f"  {line.rstrip()}")
                else:
                    print("未找到明显的错误信息")
                
                # 显示日志最后部分
                print("构建日志最后30行:")
                for line in lines[-30:]:
                    print(line.rstrip())
        else:
            print("无构建日志文件")
            
            # 检查.buildozer日志
            buildozer_logs = list(self.project_root.glob(".buildozer/**/*.log"))
            if buildozer_logs:
                print("找到的Buildozer日志文件:")
                for log in buildozer_logs:
                    print(f"  - {log}")
    
    def _run_command(self, command: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
        """运行命令"""
        try:
            print(f"执行命令: {command}")
            
            if capture:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, 
                    timeout=1800, cwd=self.project_root  # 30分钟超时
                )
                if result.stdout:
                    print(f"输出: {result.stdout[-1000:]}")  # 显示最后1000字符
                if result.stderr:
                    print(f"错误: {result.stderr[-1000:]}")
            else:
                result = subprocess.run(
                    command, shell=True, timeout=1800, cwd=self.project_root
                )
            
            if check and result.returncode != 0:
                raise BuildError(f"命令执行失败: {command} (退出码: {result.returncode})")
                
            return result
            
        except subprocess.TimeoutExpired:
            raise BuildError(f"命令执行超时: {command}")
        except Exception as e:
            raise BuildError(f"命令执行失败: {command} - {e}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python build_utils.py [setup-environment|run-build|check-result]")
        sys.exit(1)
    
    command = sys.argv[1]
    utils = BuildUtils()
    
    try:
        if command == "setup-environment":
            utils.setup_build_environment()
        elif command == "run-build":
            success = utils.run_build()
            sys.exit(0 if success else 1)
        elif command == "check-result":
            success = utils.check_build_result()
            sys.exit(0 if success else 1)
        else:
            print(f"未知命令: {command}")
            sys.exit(1)
    except BuildError as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
