# -*- coding:utf-8 -*-

import os
import subprocess
import datetime
import shlex
import json

from pathlib import Path
from pathlib import PurePath


class Thumb:
    def __init__(self, video_path, tp, remove, font="./font/Arial.ttf",
                 _debug=False):
        """
        :param video_path: The path of video you want to generate thumbnails.
        :param tp: The path to store thumbnails.
        :param remove: Remove unnecessary thumbnails flag.
        :param _debug: FFmpeg report mode flag.
        """
        self.video = video_path
        self.length = self.get_length()
        self.size = self.get_size(video_path)
        self.fullname = PurePath(video_path).name
        # 此处有重复后期处理消除重复代码
        self.name = os.path.splitext(PurePath(video_path).name)[0]
        self.tp = tp
        self.path = self.gen_path()[0]
        self.remove_thumb = remove
        self._debug = "-report " if _debug else ""
        self.font = font

    def wait(self, popen: subprocess.Popen):
        while True:
            if self._debug:
                try:
                    print(popen.communicate()[0].decode())
                except ValueError:
                    pass
            else:
                pass
            if popen.poll() is not None:
                break

    def gen_path(self) -> tuple:
        """
        Generate thumbnails folder if it doesn't exist.
        :return: path, filename -> thumbnails path, video fullname
        """
        filename = os.path.basename(self.video)
        raw_video_name = os.path.splitext(filename)[0]
        thumb_folder = Path(self.tp).as_posix()
        return thumb_folder + "/" + raw_video_name, filename

    def get_length(self) -> str:
        """
        Get the duration of self.video.
        :return: duration of video in seconds.
        """
        cmd = ('ffprobe -i {} -show_entries '
               'format=duration -v quiet -of csv="p=0"')
        cmd = cmd.format(self.video)
        result = subprocess.Popen(cmd,
                                  shell=True,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)

        output, error = result.communicate()
        output = output.splitlines()[0]
        length = output.decode()
        return length

    @staticmethod
    def get_size(file):
        """
        Get the size of file.
        :param file: video, image or etc.
        :return: size_m: file size in MiB, size_g: file size in GiB
        """
        size = os.path.getsize(file)
        size = size / 1024
        size_m = size / 1024  # MiB
        size_g = size_m / 1024  # GiB
        return size_m, size_g

    def clean_thumb(self, file):
        """
        Clean thumbs in the file's folder except the file.
        :param file: The file you don't want to delete.
        :return: Boolean
        """
        if self.remove_thumb:
            files = Path(file).parent.glob("*")
            for item in files:
                if str(item.name) != Path(file).name:
                    item.unlink()
            return True
        return False

    def thumbnails(self, num) -> list:
        """
        Generate thumbnails.
        :param num: The number of thumbnails you want to get.
        :return: Thumnmails' name list.
        """
        # 创建与视频同名的文件夹
        thumb_path, filename = self.gen_path()
        try:
            Path(thumb_path).mkdir(parents=True, exist_ok=True)
        except TypeError:
            if not Path(thumb_path).exists():
                Path(thumb_path).mkdir(parents=True)

        # 生成带时间戳的截图命令
        length = int(float(self.length))
        interval = length / (num + 1)
        time_list = []
        # 生成截图时间点
        for i in range(num):
            time_list.append(interval * (i + 1))
        ffmpeg_sh = '''ffmpeg -start_at_zero -copyts -ss {:s} -i {:s} \
        -vf "drawtext=fontfile={}:fontsize=h/20:fontcolor=yellow:x=5:y=5:text='Time\\: %{{pts\\:hms}}'" \
        -vframes 1 "{:s}.png"'''

        # print(time_list)
        thumb_list = []
        for i in time_list:
            time = str(datetime.timedelta(seconds=i))
            # 按现在时间生成截图名
            time_now = str(datetime.datetime.now().strftime("%Y%m%d_%H%M%S.%f"))

            output_name = thumb_path + "/" + filename + "_" + time_now
            cmd = ffmpeg_sh.format(time, self.video, self.font, output_name)
            p = subprocess.Popen(cmd,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            # output, error = p.communicate()
            # print(output.decode())
            thumb_list.append(output_name + ".png")
            # while True:
            #     if p.poll() is not None:
            #         break
            self.wait(p)

        return thumb_list

    def combine_thumbs(self, thumb_list, horizontal=3, vertical=3):
        """

        :param thumb_list:
        :param horizontal:
        :param vertical:
        :return:
        """
        # p = Path(path)
        path = str(PurePath(thumb_list[0]).parent)

        # 获取截图的当前目录名，作为合并截图的名字，即视频名。
        pic_name = PurePath(path).name

        # 创建一个list,用
        thumbs_name = []

        for file in thumb_list:
            thumb = PurePath(str(file)).name
            thumbs_name.append(thumb)

        i = 0
        # 创建一个二维数组
        grid_thumb = [["" for i in range(horizontal)] for i in range(vertical)]
        for v in range(len(grid_thumb)):
            for h in range(len(grid_thumb[0])):
                grid_thumb[v][h] = ' -i ' + thumbs_name[i]
                i += 1

        line = []
        i = 0
        # 生成合并每行的命令并存储在line中，生成row_x.png形式的图片
        # item: List[int]

        row_thumb = []
        for item in grid_thumb:
            cmd = 'ffmpeg -y'
            cmd += ''.join(item)
            cmd += ' -filter_complex "hstack=inputs={:s}" row_{:s}.png'
            cmd = cmd.format(str(horizontal), str(i))
            row_thumb.append("row_{:s}.png".format(str(i)))
            line.append(cmd)
            i += 1

        # 执行存储在line中的命令
        for item in line:
            pipe = subprocess.Popen(item,
                                    shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    cwd=path)
            # while True:
            #     if pipe.poll() is not None:
            #         break
            self.wait(pipe)

        cmd = 'ffmpeg -y -i '
        cmd += ' -i '.join(row_thumb)
        cmd += ' -filter_complex "vstack=inputs={:s}" {:s}.png'
        cmd = cmd.format(str(horizontal), pic_name)
        pipe = subprocess.Popen(cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                cwd=path)
        # while True:
        #     if pipe.poll() is not None:
        #         break
        self.wait(pipe)
        pic_path = PurePath(path + '/{:s}.png'.format(pic_name))

        self.clean_thumb(str(pic_path))

        return pic_path

    def add_background(self, pic_path: PurePath) -> PurePath:
        # 使用ffprobe获得mediainfo？或者从文件名中提取
        ffprobe_cmd = ('ffprobe '
                       '-i {video} '
                       '-v quiet '
                       '-print_format json '
                       '-show_format '
                       '-show_streams '
                       '-hide_banner')
        ffprobe_cmd = ffprobe_cmd.format(video=self.video)

        mediainfo = subprocess.Popen(ffprobe_cmd,
                                     shell=True,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT,
                                     )
        output, error = mediainfo.communicate()
        # print(output)
        output = json.loads(output.decode())

        v_codec = output["streams"][0]["codec_name"].upper()
        a_codec = output["streams"][1]["codec_name"].upper()
        # duration = output["format"]["duration"]
        # file_size = output["format"]["size"]
        resolution = str(output["streams"][0]["width"])
        resolution += " x " + str(output["streams"][0]["height"])
        duration = str(datetime.timedelta(seconds=int(float(self.length))))
        # 判断视频体积以决定输出单位
        file_size = str(round(self.size[0], 2)) + " MiB"
        file_size = (file_size
                     if self.size[0] < 1024.0
                     else str(round(self.size[1], 2)) + " GiB")
        # PurePath("background.png")
        cmd_dict = {  # "background": "background.png",
            "input": pic_path.as_posix(),
            "file_name": self.fullname,
            "file_size": file_size,
            "resolution": resolution,
            "height": str(output["streams"][0]["height"]),
            "width": str(output["streams"][0]["width"]),
            "v_codec": v_codec,
            "a_codec": a_codec,
            "duration": duration.replace(":", "\\\\:"),
            "output": self.path + "/" + self.name + "_full.png",
            "debug": self._debug,
            "font": self.font
        }

        cmd = '''ffmpeg {debug}-i banner.png -i {input} -filter_complex "[1:v][0:v]scale2ref=w=iw:h=iw/mdar[input1][input0];[input0]pad=x=0:y=0:w=in_w:h=4184/{width}*{height}+520[out0];[out0]drawtext=bordercolor=black@0.2:fontsize=50:fontcolor=black:fontfile="{font}":x=550:y=100:line_spacing=20:text='File\ Name\x09\\\:\ {file_name}\nFile\ Size\x09\x09\\\\:\ {file_size}\nResolution\x09\\\\:\ {resolution}\nCodec\x09\x09\x09\\\\:\ Video\ {v_codec}\\\\\,\ Audio\ {a_codec}\nDuration\x09\x09\\\\:\ {duration}\n'[out1];[out1][input1]overlay=0:H-h[out2];[out2]scale=-1:1080[out]" -map "[out]" -frames:v 1 {output} -y'''.format(
            **cmd_dict)

        # print(cmd)
        cmd_list = shlex.split(cmd)
        # print(cmd_list)

        background = subprocess.Popen(cmd_list,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT,
                                      cwd=str(Path(".").cwd()))
        output, error = background.communicate()
        print(output.decode())
        # while True:
        #     if background.poll() is not None:
        #         break
        self.wait(background)

        return PurePath(cmd_dict["output"])

    def creat(self, horizontal=3, vertical=3) -> PurePath:
        num = horizontal * vertical
        thumb_list = self.thumbnails(num)
        print(thumb_list)
        pic_path = self.combine_thumbs(thumb_list)
        return self.add_background(pic_path)

    def clean(self,
              all_pic=False, slice_pic=True, row_pic=False, final_pic=False):
        def check_input():
            if all_pic:
                return 0
            else:
                return 1

        p, filename = self.gen_path()
        p_ = Path(p)
        if check_input() == 0:
            for all_file in p_.glob('*.png'):
                os.remove(str(all_file))
        elif slice_pic:
            for slice_file in p_.glob('*.png'):
                if filename + ".mp4" in str(slice_file):
                    # In Python 3.6, you can pass Path type object  directly to os.remove()
                    os.remove(slice_file.__str__())
        elif row_pic:
            for row_file in p_.glob('*.png'):
                if "row_" in str(row_file):
                    os.remove(row_file.__str__())
        elif final_pic:
            os.remove(filename + ".png")
