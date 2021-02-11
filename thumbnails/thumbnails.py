# -*- coding:utf-8 -*-

import os
import shlex
import datetime
import subprocess
import tempfile

from typing import Tuple, Iterator
from pathlib import Path
from pathlib import PurePath

import pkg_resources
import ffmpeg

from pymediainfo import MediaInfo

# In fact, we just need ffmpeg module,
# but this module provide some useful feature.


class Video:
    __slots__ = ['__video_path', '__media_info', '__general_info',
                 '__video_info', '__audio_info']

    def __init__(self, video_path: str):
        """
        The class of video to handle video info.
        :param video_path: The path of the video you want to get its mediainfo.
        """
        self.__video_path = PurePath(video_path)
        self.__media_info = (MediaInfo.parse(self.__video_path.as_posix())
                             .to_data())
        self.__general_info = self.__media_info['tracks'][0]
        self.__video_info = self.__media_info['tracks'][1]
        self.__audio_info = self.__media_info['tracks'][2]

    @property
    def video_path(self) -> PurePath:
        """
        This method return video path.
        :return: video_path
        """
        return self.__video_path

    @property
    def duration(self) -> Tuple[float, str]:
        """
        This method return a tuple containing duration in millisecond and
        duration readable (HH:MM:SS.SS).
        example: (7193918, 01:59:53.919)
        :return: (duration, other_duration[3])
        """
        return (float(self.__general_info['duration']),
                self.__general_info['other_duration'][3])

    @property
    def size(self) -> Tuple[int, str]:
        """
        This method return a tuple containing file size in bytes and file size
        readable.
        example: (7119725816, '6.63 GiB')
        :return: (file_size, other_file_size)
        """
        return (int(self.__general_info['file_size']),
                self.__general_info['other_file_size'][0])

    @property
    def video_codec(self) -> Tuple[str, str]:
        """
        This method return a tuple containing video codecs and internet media
        type.
        example: ('AVC', 'H264')
        :return: (video_codecs, internet_media_type[6:])
        """
        return (self.__general_info['codecs_video'],
                self.__video_info['internet_media_type'][6:])

    @property
    def audio_codec(self) -> Tuple[str, str, str]:
        """
         This method return a tuple containing audio codecs, audio format and
         audio muxing mode.
         example: ('AAC LC', 'AAC', 'ADTS')
        :return: (audio_codecs, audio_format, audio_muxing_mode)
        """
        return (self.__general_info['audio_codecs'],
                self.__audio_info['format'],
                self.__audio_info['muxing_mode'])

    @property
    def resolution(self) -> Tuple[dict, str, str]:
        """
        This method return a tuple containing video width and height, video
        resolution and video display aspect ratio.
        example: ({'width': 1920, 'height': 1080}, '1920x1080', '16:9')
        :return: ({'width': width, 'height': height}, resolution, aspect_ratio)
        """
        width = self.__video_info['width']
        height = self.__video_info['height']
        return ({'width': width, 'height': height},
                str(width) + 'x' + str(height),
                self.__video_info['other_display_aspect_ratio'][0])

    @property
    def fps(self) -> str:
        """
        This method return a string containing video frame rate.
        example: '25.000'
        :return: frame_rate
        """
        return self.__video_info['frame_rate']

    @property
    def name(self) -> Tuple[str, str]:
        """
        This method return a tuple containing video path without extension and
        video name with path.
        example: ("c:/test", "test.mp4")
        :return: (video_path_stem, video_name)
        """
        return self.__video_path.stem, self.__video_path.name


class Thumb:
    def __init__(self, video_path: str, tp: str, keep: bool, font: str,
                 banner: str, _debug: bool):
        """
        The class to generate thumbnails.
        :param video_path: The path of video you want to generate thumbnails.
        :param banner: Set a banner for thumbnails.
        :param tp: The path to store thumbnails.
        :param keep: keep all temporary thumbnails.
        :param font: Set font to use in thumbnails.
        :param _debug: debug mode.
        """
        self.__video: 'Video' = Video(video_path)
        self.__stream: ffmpeg.Stream = ffmpeg.input(self.__video.video_path)
        self.__duration: Tuple[float, str] = self.__video.duration
        self.__size: Tuple[int, str] = self.__video.size
        # raw name
        self.__name = self.__video.name[0]
        # name with ext
        self.__name_ext = self.__video.name[1]
        # output path
        self.__tp = os.getcwd() if tp == "." else tp
        self.__remove_thumb = not keep
        self.__debug = "-report " if _debug else ""
        if not font:
            self.__font = PurePath(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                if os.name == "posix"
                else "C:/Windows/Fonts/arial.ttf")
        else:
            self.__font = PurePath(font)

        self.__banner = PurePath(banner).as_posix()
        self.__default_banner = (
            True if banner == "thumbnails/static/banner.png"
            else False)

        resource_package = __name__
        resource_path = '/'.join(
            ('static', 'banner.png'))  # Do not use os.path.join()
        banner_path = pkg_resources.resource_filename(resource_package,
                                                      resource_path)
        if self.__default_banner:
            self.__banner = PurePath(banner_path).as_posix()

    def wait(self, popen: subprocess.Popen):
        """

        :param popen:
        :return:
        """
        while True:
            if self.__debug:
                try:
                    print(popen.communicate()[0].decode())
                except ValueError:
                    pass
            else:
                pass
            if popen.poll() is not None:
                break

    def __gen_directory(self, td) -> str:
        """
        Generate thumbnails folder if it doesn't exist.
        :return: path, filename -> thumbnails path, video fullname
        """
        # self.remove_thumb=False 时创建与视频同名的文件夹
        if not self.__remove_thumb:
            thumb_path = PurePath(self.__tp).as_posix() + "/" + self.__name
            try:
                Path(thumb_path).mkdir(parents=True, exist_ok=True)
            except TypeError:
                if not Path(thumb_path).exists():
                    Path(thumb_path).mkdir(parents=True)
        else:
            thumb_path = td
        return thumb_path

    def thumbnails(self, num: int, td: str) -> Iterator:
        """
        Generate thumbnails.
        :param num: The number of thumbnails you want to get.
        :param td: temporary directory.
        :return: Thumbnails' name list.
        """

        def output_path(index):
            return PurePath(thumb_path
                            + "/"
                            + self.__name
                            + "_"
                            + str(index)
                            + '.png').as_posix()
        thumb_path = self.__gen_directory(td)

        # 生成带时间戳的截图命令
        interval = int(self.__duration[0]/1000) / (num + 1)

        # 生成截图时间点
        time_list = enumerate([interval * (i + 1) for i in range(num)], start=1)

        thumb_list = [(ffmpeg.input(self.__video.video_path.as_posix(),
                                    start_at_zero=None,
                                    ss=datetime.timedelta(seconds=time_point),
                                    copyts=None)
                       .drawtext(text="Time: %{pts:hms}", x=5, y=5,
                                 escape_text=False,
                                 fontsize="h/20",
                                 fontcolor="yellow",
                                 fontfile=self.__font.as_posix())
                       .output(output_path(index), vframes=1, loglevel=48)
                       .overwrite_output()
                       .run_async(quiet=True),
                       output_path(index))
                      for index, time_point in time_list]

        # for pipe in thumb_list:
        #     self.wait(pipe[0])

        return map(lambda x: x[1], thumb_list)

    def combine_thumbs(self, thumb_list, td, horizontal=3, vertical=3):
        """

        :param thumb_list:
        :param td:
        :param horizontal:
        :param vertical:
        :return:
        """
        path = self.__gen_directory(td)

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
        cmd = cmd.format(str(horizontal), self.__name)
        pipe = subprocess.Popen(cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                cwd=path)
        self.wait(pipe)
        pic_path = PurePath(path + '/{:s}.png'.format(self.__name))
        return pic_path

    def add_banner(self, pic_path: PurePath) -> PurePath:
        if not self.__remove_thumb:
            output_path = PurePath(self.__tp).as_posix() + "/" + self.__name
        else:
            output_path = PurePath(self.__tp).as_posix()

        cmd_dict = {
            "input": pic_path.as_posix(),
            "file_name": self.__name_ext,
            "file_size": self.__size[1],
            "width": self.__video.resolution[0]['width'],
            "height": self.__video.resolution[0]['height'],
            "resolution": self.__video.resolution[1],
            "v_codec": self.__video.video_codec[1],
            "a_codec": self.__video.audio_codec[1],
            "duration": self.__duration[1].replace(":", "\\\\:"),
            "output": output_path + "/" + self.__name + "_full.png",
            "debug": self.__debug,
            "font": self.__font,
            "banner": self.__banner
        }
        if not self.__default_banner:
            cmd = ('''ffmpeg {debug}-i {banner} -i {input} '''
                   '''-filter_complex "[1:v][0:v]scale2ref=w=iw:h=iw/mdar[input1][input0];'''
                   '''[input0]pad=x=0:y=0:w=in_w:h=4184/{width}*{height}+520[out0];'''
                   '''[out0]drawtext=bordercolor=black@0.2:fontsize=50:fontcolor=black:'''
                   '''fontfile="{font}":x=550:y=100:line_spacing=20:'''
                   '''text='File\ Name\x09\\\\:\ {file_name}\nFile\ Size'''
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
                   '''text='File\ Name\x09\\\\:\ {file_name}\nFile\ '''
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

    def create(self, horizontal=3, vertical=3) -> PurePath:
        num = horizontal * vertical
        with tempfile.TemporaryDirectory() as td:
            thumb_list = self.thumbnails(num, td)
            pic_path = self.combine_thumbs(thumb_list, td)
            return self.add_banner(pic_path)
