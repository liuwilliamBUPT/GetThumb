# -*- coding:utf-8 -*-

import argparse
import sys

from thumbnails.thumbnails import Thumb


def main():
    APP_DESC = r"""
     _____        _    _____  _                        _                    _  _      
    |  __ \      | |  |_   _|| |                      | |                  (_)| |     
    | |  \/  ___ | |_   | |  | |__   _   _  _ __ ___  | |__   _ __    __ _  _ | | ___ 
    | | __  / _ \| __|  | |  | '_ \ | | | || '_ ` _ \ | '_ \ | '_ \  / _` || || |/ __|
    | |_\ \|  __/| |_   | |  | | | || |_| || | | | | || |_) || | | || (_| || || |\__ \
     \____/ \___| \__|  \_/  |_| |_| \__,_||_| |_| |_||_.__/ |_| |_| \__,_||_||_||___/     
    
    一款基于FFmpeg的缩略图截图工具 A FFmpeg based thumbnails tool
    注意banner功能仅为测试功能 Note: Getting thumbnails with a banner is still under testing.
    """
    if len(sys.argv) == 1:
        print(APP_DESC)
        sys.argv.append('--help')
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help="指定需要的截图文件", required=True)
    parser.add_argument('-o', '--output', help="指定输出目录", default=".")
    parser.add_argument('-b', '--banner', help="指定banner",
                        default="thumbnails/static/banner.png")
    parser.add_argument('-t', '--font', help="指定字体文件")
    parser.add_argument('-d', '--debug', help="启动FFmpeg的debug模式",
                        action='store_true')
    parser.add_argument('-r', '--reserve', help="保留多余的单张截图",
                        action='store_false')

    args = parser.parse_args()
    Thumb(video_path=args.file,
          tp=args.output,
          remove=args.reserve,
          font=args.file,
          banner=args.banner,
          _debug=args.debug).creat()
    return


if __name__ == '__main__':
    main()
