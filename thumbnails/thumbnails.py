# -*- coding:utf-8 -*-

import os
import subprocess
import datetime
import shlex
import json
import pkg_resources
import tempfile

from pathlib import Path
from pathlib import PurePath


class Thumb:
    def __init__(self, video_path, banner, tp, keep, font, _debug):
        """
        :param video_path: The path of video you want to generate thumbnails.
        :param banner: Set a banner for thumbnails.
        :param tp: The path to store thumbnails.
        :param keep: keep all temporary thumbnails.
        :param font: Set font to use in thumbnails.
        :param _debug: FFmpeg report mode.
        """
        self.video = video_path
        self.length = self.get_length()
        self.size = self.get_size(video_path)
        # raw name
        self.name = PurePath(video_path).stem
        # name with ext
        self.name_ext = PurePath(video_path).name
        # output path
        self.tp = tp
        self.remove_thumb = not keep
        self._debug = "-report " if _debug else ""
        if not font:
            self.font = ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                         if os.name == "posix"
                         else "C:/Windows/Fonts/arial.ttf")
        else:
            self.font = font
        self.banner = banner
        self.default_banner = True if banner == "thumbnails/static/banner.png" else False

        resource_package = __name__
        resource_path = '/'.join(
            ('static', 'banner.png'))  # Do not use os.path.join()
        banner_path = pkg_resources.resource_filename(resource_package,
                                                      resource_path)
        if self.default_banner:
            self.banner = banner_path

    def wait(self, popen: subprocess.Popen):
        """

        :param popen:
        :return:
        """
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

    def gen_path(self, td) -> str:
        """
        Generate thumbnails folder if it doesn't exist.
        :return: path, filename -> thumbnails path, video fullname
        """
        # self.remove_thumb=False时创建与视频同名的文件夹
        if not self.remove_thumb:
            thumb_path = PurePath(self.tp).as_posix() + "/" + self.name
            try:
                Path(thumb_path).mkdir(parents=True, exist_ok=True)
            except TypeError:
                if not Path(thumb_path).exists():
                    Path(thumb_path).mkdir(parents=True)
        else:
            thumb_path = td
        return thumb_path

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

    def thumbnails(self, num, td) -> list:
        """
        Generate thumbnails.
        :param num: The number of thumbnails you want to get.
        :param td: temporary directory.
        :return: Thumbnails' name list.
        """
        thumb_path = self.gen_path(td)

        # 生成带时间戳的截图命令
        length = int(float(self.length))
        interval = length / (num + 1)
        time_list = []

        # 生成截图时间点
        for i in range(num):
            time_list.append(interval * (i + 1))
        ffmpeg_sh = ('''ffmpeg -start_at_zero -copyts -ss {:s} -i {:s} '''
                     '''-vf "drawtext=fontfile={}:fontsize=h/20:'''
                     '''fontcolor=yellow:x=5:y=5:'''
                     '''text='Time\\: %{{pts\\:hms}}'" -vframes 1 "{:s}.png"''')

        thumb_list = []
        for time_point in time_list:
            time = str(datetime.timedelta(seconds=time_point))
            # 按现在时间生成截图名
            time_now = str(datetime.datetime.now().strftime("%Y%m%d_%H%M%S.%f"))

            output_name = thumb_path + "/" + self.name + "_" + time_now
            cmd = ffmpeg_sh.format(time, self.video, self.font, output_name)
            p = subprocess.Popen(cmd,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            thumb_list.append(output_name + ".png")
            self.wait(p)

        return thumb_list

    def combine_thumbs(self, thumb_list, td, horizontal=3, vertical=3):
        """

        :param thumb_list:
        :param td:
        :param horizontal:
        :param vertical:
        :return:
        """
        path = self.gen_path(td)

        # 创建一个list,用于储存截图名字，避免生成命令过长
        thumbs_name = []

        for file in thumb_list:
            thumb = PurePath(str(file)).name
            thumbs_name.append(thumb)

        i = 0
        # 创建一个二维数组
        grid_thumb = [["" for i in range(horizontal)] for i in range(vertical)]

        # 生成对应的-i 按时间顺序填入grid_thumb
        for v in range(vertical):
            for h in range(horizontal):
                grid_thumb[v][h] = ' -i ' + thumbs_name[i]
                i += 1

        # 生成合并每行的命令并存储在line中，生成row_x.png形式的图片
        line = []
        i = 0

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
            self.wait(pipe)

        cmd = 'ffmpeg -y -i '
        cmd += ' -i '.join(row_thumb)
        cmd += ' -filter_complex "vstack=inputs={:s}" {:s}.png'
        cmd = cmd.format(str(horizontal), self.name)
        pipe = subprocess.Popen(cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                cwd=path)
        self.wait(pipe)
        pic_path = PurePath(path + '/{:s}.png'.format(self.name))
        return pic_path

    def add_banner(self, pic_path: PurePath, td) -> PurePath:
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
        if not self.remove_thumb:
            output_path = PurePath(self.tp).as_posix() + "/" + self.name
        else:
            output_path = PurePath(self.tp).as_posix()

        cmd_dict = {
            "input": pic_path.as_posix(),
            "file_name": self.name_ext,
            "file_size": file_size,
            "resolution": resolution,
            "height": str(output["streams"][0]["height"]),
            "width": str(output["streams"][0]["width"]),
            "v_codec": v_codec,
            "a_codec": a_codec,
            "duration": duration.replace(":", "\\\\:"),
            "output": output_path + "/" + self.name + "_full.png",
            "debug": self._debug,
            "font": self.font,
            "banner": self.banner
        }
        if not self.default_banner:
            cmd = ('''ffmpeg {debug}-i {banner} -i {input} '''
                   '''-filter_complex "[1:v][0:v]scale2ref=w=iw:h=iw/mdar[input1][input0];'''
                   '''[input0]pad=x=0:y=0:w=in_w:h=4184/{width}*{height}+520[out0];'''
                   '''[out0]drawtext=bordercolor=black@0.2:fontsize=50:fontcolor=black:'''
                   '''fontfile="{font}":x=550:y=100:line_spacing=20:'''
                   '''text='File\ Name\x09\x09\\\\:\ {file_name}\nFile\ Size'''
                   '''\x09\x09\\\\:\ {file_size}\nResolution\x09\\\\:\ '''
                   '''{resolution}\nCodec\x09\x09\x09\\\\:\ '''
                   '''Video\ {v_codec}\\\\\,\ Audio\ {a_codec}\n'''
                   '''Duration\x09\x09\\\\:\ {duration}\n'[out1];'''
                   '''[out1][input1]overlay=0:H-h[out2];'''
                   '''[out2]scale=-1:1080[out]" '''
                   '''-map "[out]" -frames:v 1 {output} -y''').format(
                **cmd_dict)
        else:
            cmd = ('''ffmpeg {debug}-i {banner} -i {input} '''
                   '''-filter_complex "[1:v][0:v]scale2ref=w=iw:h=iw/mdar[input1][input0];'''
                   '''[input0]pad=x=0:y=0:w=in_w:h=4168/{width}*{height}+1000[out0];'''
                   '''[out0]drawtext=bordercolor=black@0.2:fontsize=50:fontcolor=0xD5246B:'''
                   '''fontfile="{font}":x=200:y=640:line_spacing=20:'''
                   '''text='File\ Name\x09\x09\\\\:\ {file_name}\nFile\ '''
                   '''Size\x09\x09\\\\:\ {file_size}\n'''
                   '''Resolution\x09\\\\:\ {resolution}\n'''
                   '''Codec\x09\x09\x09\\\\:\ Video\ {v_codec}\\\\\,\ Audio\ {a_codec}\n'''
                   '''Duration\x09\x09\\\\:\ {duration}\n'[out1];'''
                   '''[out1][input1]overlay=0:H-h[out2];[out2]scale=-1:1080[out]" '''
                   '''-map "[out]" -frames:v 1 {output} -y''').format(
                **cmd_dict)

        cmd_list = shlex.split(cmd)
        banner = subprocess.Popen(cmd_list,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  cwd=str(Path(".").cwd()))
        self.wait(banner)

        return PurePath(cmd_dict["output"])

    def creat(self, horizontal=3, vertical=3) -> PurePath:
        num = horizontal * vertical
        with tempfile.TemporaryDirectory()as td:
            thumb_list = self.thumbnails(num, td)
            pic_path = self.combine_thumbs(thumb_list, td)
            return self.add_banner(pic_path, td)
