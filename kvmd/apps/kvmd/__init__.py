# ========================================================================== #
#                                                                            #
#    KVMD - The main PiKVM daemon.                                           #
#                                                                            #
#    Copyright (C) 2018-2022  Maxim Devaev <mdevaev@gmail.com>               #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU General Public License as published by    #
#    the Free Software Foundation, either version 3 of the License, or       #
#    (at your option) any later version.                                     #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU General Public License for more details.                            #
#                                                                            #
#    You should have received a copy of the GNU General Public License       #
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.  #
#                                                                            #
# ========================================================================== #


from typing import List
from typing import Optional

from kvmd.apps import init
from kvmd.apps.kvmd.auth import AuthManager
from kvmd.apps.kvmd.info import InfoManager
from kvmd.apps.kvmd.logreader import LogReader
from kvmd.apps.kvmd.server import KvmdServer
from kvmd.apps.kvmd.snapshoter import Snapshoter
from kvmd.apps.kvmd.streamer import Streamer
from kvmd.apps.kvmd.tesseract import TesseractOcr
from kvmd.apps.kvmd.ugpio import UserGpio
from kvmd.logging import get_logger
from kvmd.plugins.atx import get_atx_class
from kvmd.plugins.hid import get_hid_class


# from ...logging import get_logger


# =====
def main(argv: Optional[List[str]]=None) -> None:
    config = init(
        prog="kvmd",
        description="The main PiKVM daemon",
        argv=argv,
        check_run=True,
        load_auth=True,
        load_hid=True,
        load_atx=True,
        load_msd=True,
        load_gpio=True,
    )[2]

    msd_kwargs = config.kvmd.msd._unpack(ignore=["type"])
    if config.kvmd.msd.type == "otg":
        msd_kwargs["gadget"] = config.otg.gadget  # XXX: Small crutch to pass gadget name to the plugin

    hid_kwargs = config.kvmd.hid._unpack(ignore=["type", "keymap", "ignore_keys", "mouse_x_range", "mouse_y_range"])
    if config.kvmd.hid.type == "otg":
        hid_kwargs["udc"] = config.otg.udc  # XXX: Small crutch to pass UDC to the plugin

    global_config = config
    config = config.kvmd

    hid = get_hid_class(config.hid.type)(**hid_kwargs)
    streamer = Streamer(
        **config.streamer._unpack(ignore=["forever", "desired_fps", "resolution", "h264_bitrate", "h264_gop"]),
        **config.streamer.resolution._unpack(),
        **config.streamer.desired_fps._unpack(),
        **config.streamer.h264_bitrate._unpack(),
        **config.streamer.h264_gop._unpack(),
    )

    KvmdServer(
        auth_manager=AuthManager(
            internal_type=config.auth.internal.type,
            internal_kwargs=config.auth.internal._unpack(ignore=["type", "force_users"]),
            external_type=config.auth.external.type,
            external_kwargs=(config.auth.external._unpack(ignore=["type"]) if config.auth.external.type else {}),
            force_internal_users=config.auth.internal.force_users,
            enabled=config.auth.enabled,
        ),
        info_manager=InfoManager(global_config),
        log_reader=LogReader(),
        # user_gpio=UserGpio(config.gpio, global_config.otg),
        ocr=TesseractOcr(**config.ocr._unpack()),

        hid=hid,
        # atx=get_atx_class(config.atx.type)(**config.atx._unpack(ignore=["type"])),
        # msd=get_msd_class(config.msd.type)(**msd_kwargs),
        streamer=streamer,

        snapshoter=Snapshoter(
            hid=hid,
            streamer=streamer,
            **config.snapshot._unpack(),
        ),

        keymap_path=config.hid.keymap,
        ignore_keys=config.hid.ignore_keys,
        mouse_x_range=(config.hid.mouse_x_range.min, config.hid.mouse_x_range.max),
        mouse_y_range=(config.hid.mouse_y_range.min, config.hid.mouse_y_range.max),

        stream_forever=config.streamer.forever,
    ).run(**config.server._unpack())

    get_logger(0).info("Bye-bye")
