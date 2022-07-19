
import asyncio
import logging
from typing import Any, Optional, List
from hummingbot.core.utils.async_call_scheduler import AsyncCallScheduler
from hummingbot.core.utils.async_utils import safe_ensure_future
from hummingbot.logger.logger import HummingbotLogger
from hummingbot.client.restapi import restapp_aiohttp as web_server

DISABLED_COMMANDS = {
    "connect",             # disabled because telegram can't display secondary prompt
    "create",              # disabled because telegram can't display secondary prompt
    "import",              # disabled because telegram can't display secondary prompt
    "export",              # disabled for security
}


class RestAppBot:
    app_logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls.app_logger is None:
            cls.app_logger = logging.getLogger(__name__)
        return cls.app_logger

    def __init__(self,
                 hb: "hummingbot.client.hummingbot_application.HummingbotApplication") -> None:
        super().__init__()
        self._started = False
        self._hb = hb
        self._ev_loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self._async_call_scheduler = AsyncCallScheduler.shared_instance()
        self._msg_queue: asyncio.Queue = asyncio.Queue()
        self._send_msg_task: Optional[asyncio.Task] = None

    def start(self):
        if not self._started:
            self._started = True
            # start web server
            self._web_server_task = safe_ensure_future(web_server.main(self.handler_loop, self.get_all_msgs_from_queue),
                                                       loop=self._ev_loop)
            self._send_msg_task = None  # safe_ensure_future(self.send_msg_from_queue(), loop=self._ev_loop)
            self.logger().info("Telegram is listening...")

    def stop(self) -> None:
        if self._started:
            # stop web server
            self._web_server_task.cancel()
        if self._send_msg_task:
            self._send_msg_task.cancel()

    def handler(self, msg: dict) -> None:
        safe_ensure_future(self.handler_loop(msg), loop=self._ev_loop)

    async def handler_loop(self, msg: dict) -> None:
        async_scheduler: AsyncCallScheduler = AsyncCallScheduler.shared_instance()
        try:
            input_text = msg['cmd'].strip()
            output = f"\n[RestApp Input] {input_text}"

            self._hb.app.log(output)

            # if the command does starts with any disabled commands
            if any([input_text.lower().startswith(dc) for dc in DISABLED_COMMANDS]):
                self.add_msg_to_queue(f"Command {input_text} is disabled from telegram")
            else:
                await async_scheduler.call_async(self._hb._handle_command, input_text)
        except Exception as e:
            self.add_msg_to_queue(str(e))

    @staticmethod
    def _divide_chunks(arr: List[Any], n: int = 5):
        """ Break a list into chunks of size N """
        for i in range(0, len(arr), n):
            yield arr[i:i + n]

    def add_msg_to_queue(self, msg: str):
        self._msg_queue.put_nowait(msg)
        # lines: List[str] = msg.split("\n")
        # msg_chunks: List[List[str]] = self._divide_chunks(lines, 30)
        # for chunk in msg_chunks:
        #     self._msg_queue.put_nowait("\n".join(chunk))

    async def get_msg_from_queue(self):
        new_msg: str = await self._msg_queue.get()
        return new_msg

    async def get_all_msgs_from_queue(self):
        msgs = []
        while not self._msg_queue.empty():
            new_msg: str = await self._msg_queue.get()
            msgs.append(new_msg)
        return msgs

    async def send_msg_from_queue(self):
        while True:
            try:
                new_msg: str = await self._msg_queue.get()
                if isinstance(new_msg, str) and len(new_msg) > 0:
                    await self.send_msg_async(new_msg)
            except Exception as e:
                self.logger().error(str(e))
            await asyncio.sleep(1)

    async def send_msg_async(self, msg: str) -> None:
        """
        Send given markdown message
        """
        try:
            await self._async_call_scheduler.call_async(lambda: print("web response: ", msg))
        except Exception as e:
            self.logger().network(f"WebAppError: {e.message}! Giving up on that message.", exc_info=True)