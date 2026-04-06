#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金价格定时推送脚本
从极速API获取伦敦金价格，定时推送到微信
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime
from typing import Optional, Dict, Any

import requests
import schedule

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gold_price_pusher.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')


class GoldPricePusher:
    """黄金价格推送器"""

    def __init__(self, config_path: str = CONFIG_FILE):
        """初始化推送器"""
        self.config = self._load_config(config_path)
        self.last_price: Optional[float] = None

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"配置加载成功: {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"配置文件不存在: {config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            raise

    def _get_wechat_user_id(self) -> str:
        """获取微信用户ID，优先从环境变量读取"""
        user_id = os.environ.get('WECHAT_USER_ID')
        if user_id:
            logger.info("从环境变量获取微信用户ID")
            return user_id
        user_id = self.config.get('wechat_user_id', '')
        if user_id == 'YOUR_WECHAT_USER_ID':
            logger.warning("请配置微信用户ID（环境变量WECHAT_USER_ID或config.json）")
        return user_id

    def fetch_gold_price(self) -> Optional[Dict[str, Any]]:
        """从API获取黄金价格"""
        url = self.config['api_url']
        api_key = self.config['api_key']

        params = {'appkey': api_key}
        max_attempts = self.config['retry']['max_attempts']
        delay = self.config['retry']['delay_seconds']

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"正在获取黄金价格（第{attempt}次尝试）...")
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()

                if data.get('status') != 0:
                    logger.error(f"API返回错误: {data.get('msg', '未知错误')}")
                    return None

                # 查找伦敦金数据
                result_list = data.get('result', [])
                for item in result_list:
                    if item.get('type') == '伦敦金':
                        price_info = {
                            'price': float(item.get('price', 0)),
                            'change': item.get('change', '0'),
                            'changepercent': item.get('changepercent', '0%'),
                            'type': item.get('type', ''),
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        logger.info(f"获取成功: 伦敦金价格 ${price_info['price']}")
                        return price_info

                logger.error("未找到伦敦金数据")
                return None

            except requests.RequestException as e:
                logger.error(f"请求失败: {e}")
                if attempt < max_attempts:
                    logger.info(f"等待{delay}秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"已达到最大重试次数({max_attempts})，获取失败")
                    return None
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"数据解析失败: {e}")
                return None

        return None

    def convert_price(self, usd_price: float) -> float:
        """将美元/盎司转换为人民币/克"""
        ounces_to_grams = self.config['conversion']['ounces_to_grams']
        usd_to_cny = self.config['conversion']['usd_to_cny']

        # 人民币/克 = 美元/盎司 ÷ 盎司转克 × 美元转人民币
        cny_per_gram = usd_price / ounces_to_grams * usd_to_cny
        return round(cny_per_gram, 2)

    def calculate_change(self, current_price: float) -> Optional[Dict[str, float]]:
        """计算价格变化"""
        if self.last_price is None:
            self.last_price = current_price
            return None

        change = current_price - self.last_price
        change_percent = (change / self.last_price) * 100 if self.last_price != 0 else 0

        result = {
            'change': round(change, 2),
            'change_percent': round(change_percent, 2)
        }

        self.last_price = current_price
        return result

    def send_message(self, text: str) -> bool:
        """通过OpenClaw发送消息"""
        user_id = self._get_wechat_user_id()
        if not user_id or user_id == 'YOUR_WECHAT_USER_ID':
            logger.error("未配置微信用户ID，无法发送消息")
            return False

        try:
            cmd = [
                'openclaw', 'message', 'send',
                '--channel', 'openclaw-weixin',
                '--to', user_id,
                '--text', text
            ]

            logger.info(f"正在发送消息到: {user_id}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info("消息发送成功")
                return True
            else:
                logger.error(f"消息发送失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("发送消息超时")
            return False
        except FileNotFoundError:
            logger.error("未找到openclaw命令，请确保已安装OpenClaw")
            return False
        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return False

    def format_message(self, price_info: Dict[str, Any], cny_price: float,
                       price_change: Optional[Dict[str, float]] = None) -> str:
        """格式化推送消息"""
        lines = [
            "💰 黄金价格播报",
            f"📅 时间: {price_info['time']}",
            "",
            f"🥇 伦敦金: ${price_info['price']:.2f}/盎司",
            f"💴 人民币: ¥{cny_price}/克",
        ]

        # API返回的涨跌幅
        if price_info.get('changepercent'):
            change_pct = price_info['changepercent']
            if change_pct.startswith('-'):
                lines.append(f"📉 涨跌幅: {change_pct}")
            else:
                lines.append(f"📈 涨跌幅: +{change_pct}")

        # 本地计算的变化（如果有）
        if price_change:
            change_emoji = "🔴" if price_change['change'] < 0 else "🟢"
            sign = "" if price_change['change'] < 0 else "+"
            lines.append(f"{change_emoji} 较上次: {sign}{price_change['change']:.2f} ({sign}{price_change['change_percent']:.2f}%)")

        lines.append("")
        lines.append("--- 黄金价格定时推送 ---")

        return "\n".join(lines)

    def run_once(self) -> bool:
        """执行一次价格获取和推送"""
        logger.info("=" * 50)
        logger.info("开始执行黄金价格推送任务")

        # 获取价格
        price_info = self.fetch_gold_price()
        if not price_info:
            logger.error("获取价格失败，本次推送取消")
            return False

        # 价格换算
        usd_price = price_info['price']
        cny_price = self.convert_price(usd_price)

        # 计算变化
        price_change = self.calculate_change(cny_price)

        # 格式化消息
        message = self.format_message(price_info, cny_price, price_change)
        logger.info(f"消息内容:\n{message}")

        # 发送消息
        return self.send_message(message)

    def setup_schedule(self):
        """设置定时任务"""
        morning = self.config['schedule']['morning']
        afternoon = self.config['schedule']['afternoon']

        # 上午时段
        for hour in range(morning['start_hour'], morning['end_hour']):
            for minute in range(0, 60, morning['interval_minutes']):
                time_str = f"{hour:02d}:{minute:02d}"
                schedule.every().day.at(time_str).do(self.run_once)
                logger.info(f"已添加定时任务: {time_str}")

        # 下午时段
        for hour in range(afternoon['start_hour'], afternoon['end_hour']):
            for minute in range(0, 60, afternoon['interval_minutes']):
                time_str = f"{hour:02d}:{minute:02d}"
                schedule.every().day.at(time_str).do(self.run_once)
                logger.info(f"已添加定时任务: {time_str}")

    def run(self):
        """运行定时推送服务"""
        logger.info("黄金价格定时推送服务启动")
        self.setup_schedule()

        logger.info("定时任务列表:")
        for job in schedule.get_jobs():
            logger.info(f"  - {job}")

        logger.info("服务运行中，按 Ctrl+C 停止...")

        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到停止信号，服务退出")
        except Exception as e:
            logger.error(f"服务异常: {e}")
            raise


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='黄金价格定时推送脚本')
    parser.add_argument('--once', action='store_true', help='只执行一次，不启动定时服务')
    parser.add_argument('--test', action='store_true', help='测试模式，只获取价格不推送')
    parser.add_argument('--config', type=str, help='指定配置文件路径')

    args = parser.parse_args()

    try:
        pusher = GoldPricePusher(args.config) if args.config else GoldPricePusher()

        if args.test:
            # 测试模式：只获取价格
            logger.info("测试模式：获取价格...")
            price_info = pusher.fetch_gold_price()
            if price_info:
                cny_price = pusher.convert_price(price_info['price'])
                print("\n" + "=" * 40)
                print(f"伦敦金价格: ${price_info['price']:.2f}/盎司")
                print(f"人民币价格: ¥{cny_price}/克")
                print(f"涨跌幅: {price_info.get('changepercent', 'N/A')}")
                print("=" * 40 + "\n")
            return

        if args.once:
            # 单次执行
            pusher.run_once()
        else:
            # 启动定时服务
            pusher.run()

    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        exit(1)


if __name__ == '__main__':
    main()
