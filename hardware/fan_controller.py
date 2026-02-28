#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PWMファン制御モジュール
温度連動でファン速度を自動制御
"""

import os
import time
import logging
from typing import Optional

try:
    import RPi.GPIO as GPIO
except ImportError:
    # 開発環境用のモック
    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        
        @staticmethod
        def setmode(mode):
            pass
        
        @staticmethod
        def setup(pin, mode):
            pass
        
        @staticmethod
        def PWM(pin, freq):
            class MockPWM:
                def start(self, duty):
                    pass
                def ChangeDutyCycle(self, duty):
                    pass
                def stop(self):
                    pass
            return MockPWM()
        
        @staticmethod
        def cleanup():
            pass
    
    GPIO = MockGPIO()


class FanController:
    """PWMファン制御クラス"""
    
    # GPIO設定
    FAN_PIN = 18  # GPIO 18 (PWM0)
    PWM_FREQ = 25000  # 25kHz
    
    # 温度閾値とファン速度
    TEMP_THRESHOLDS = [
        (70, 100, "最大"),      # 70°C以上: 100% (緊急)
        (60, 75, "高速"),       # 60-70°C: 75%
        (50, 50, "中速"),       # 50-60°C: 50%
        (0, 30, "低速/停止")    # 50°C以下: 30%
    ]
    
    def __init__(self, enable_warnings: bool = True):
        """
        初期化
        
        Args:
            enable_warnings: 高温警告を有効にするか
        """
        self.logger = logging.getLogger(__name__)
        self.enable_warnings = enable_warnings
        self.pwm = None
        self.current_duty = 0
        self.last_warning_time = 0
        self.warning_cooldown = 300  # 5分間は再警告しない
        
        self._setup_gpio()
    
    def _setup_gpio(self):
        """GPIO初期化"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.FAN_PIN, GPIO.OUT)
            self.pwm = GPIO.PWM(self.FAN_PIN, self.PWM_FREQ)
            self.pwm.start(0)
            self.logger.info("PWMファン制御を初期化しました")
        except Exception as e:
            self.logger.error(f"GPIO初期化エラー: {e}")
    
    def get_cpu_temperature(self) -> float:
        """
        CPU温度を取得
        
        Returns:
            CPU温度（℃）
        """
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read().strip()) / 1000.0
                return temp
        except Exception as e:
            self.logger.error(f"CPU温度取得エラー: {e}")
            return 50.0  # デフォルト値
    
    def calculate_fan_speed(self, temperature: float) -> tuple:
        """
        温度に応じたファン速度を計算
        
        Args:
            temperature: CPU温度（℃）
            
        Returns:
            (デューティサイクル, 状態名)
        """
        for temp_threshold, duty, status in self.TEMP_THRESHOLDS:
            if temperature >= temp_threshold:
                return duty, status
        
        return 0, "停止"
    
    def set_fan_speed(self, duty_cycle: int):
        """
        ファン速度を設定
        
        Args:
            duty_cycle: デューティサイクル（0-100）
        """
        if self.pwm is None:
            return
        
        try:
            # 急激な変化を避けるため、段階的に変更
            if abs(duty_cycle - self.current_duty) > 20:
                # 20%以上の変化の場合、段階的に
                step = 5 if duty_cycle > self.current_duty else -5
                for d in range(self.current_duty, duty_cycle, step):
                    self.pwm.ChangeDutyCycle(d)
                    time.sleep(0.05)
            
            self.pwm.ChangeDutyCycle(duty_cycle)
            self.current_duty = duty_cycle
            
        except Exception as e:
            self.logger.error(f"ファン速度設定エラー: {e}")
    
    def check_and_warn(self, temperature: float) -> bool:
        """
        高温警告をチェック
        
        Args:
            temperature: CPU温度（℃）
            
        Returns:
            警告を発したかどうか
        """
        if not self.enable_warnings:
            return False
        
        if temperature >= 70:
            current_time = time.time()
            if current_time - self.last_warning_time > self.warning_cooldown:
                self.logger.error(f"🔥 CPU温度が危険レベルです: {temperature:.1f}°C")
                self.last_warning_time = current_time
                return True
        
        return False
    
    def update(self) -> dict:
        """
        ファン制御を更新
        
        Returns:
            状態情報
        """
        temperature = self.get_cpu_temperature()
        duty_cycle, status = self.calculate_fan_speed(temperature)
        self.set_fan_speed(duty_cycle)
        
        # 高温警告チェック
        warning_sent = self.check_and_warn(temperature)
        
        return {
            "temperature": temperature,
            "fan_duty": duty_cycle,
            "fan_status": status,
            "warning_sent": warning_sent
        }
    
    def get_fan_rpm(self) -> Optional[int]:
        """
        ファンRPMを取得（タコメーター信号がある場合）
        
        Returns:
            RPM値（取得できない場合はNone）
        """
        # 注: タコメーター信号の読み取りには追加のGPIOピンが必要
        # ここでは推定値を返す
        if self.current_duty == 0:
            return 0
        
        # おおよその推定: 最大RPM 5000として計算
        estimated_rpm = int(5000 * (self.current_duty / 100))
        return estimated_rpm
    
    def cleanup(self):
        """クリーンアップ"""
        if self.pwm:
            self.pwm.stop()
        GPIO.cleanup()
        self.logger.info("PWMファン制御をクリーンアップしました")


def main():
    """テスト用メイン関数"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s'
    )
    
    controller = FanController()
    
    try:
        print("PWMファン制御テスト開始（Ctrl+Cで終了）")
        while True:
            status = controller.update()
            rpm = controller.get_fan_rpm()
            
            print(f"温度: {status['temperature']:.1f}°C | "
                  f"ファン: {status['fan_status']} ({status['fan_duty']}%) | "
                  f"RPM: {rpm}")
            
            time.sleep(5)
    
    except KeyboardInterrupt:
        print("\n終了します")
    finally:
        controller.cleanup()


if __name__ == "__main__":
    main()
