from typing import Optional

from framework.renderer import Renderer


class MultipleSegmentSplitter(Renderer):
    last_commit: str = ''
    uncommitted_msg: str = ''

    async def render(self, msg: str) -> Optional[str]:
        self.uncommitted_msg = msg.removeprefix(self.last_commit)
        segments = self.uncommitted_msg.strip().split("\n")
        # Skip empty message
        if not self.uncommitted_msg.strip():
            self.last_commit = msg
            return None
        # Merge code
        if segments[0].startswith("```"):
            if len(segments) == 1:
                # Waiting for more line
                return None
            tokens = segments[0]
            for seg in segments[1:]:
                tokens = tokens + '\n' + seg
                if seg.endswith("```"):
                    # Keep left
                    self.last_commit = self.last_commit + \
                                           self.uncommitted_msg[:len(tokens) + self.uncommitted_msg.find(tokens)]
                    return tokens
            return None
        elif segments[0].startswith("$$"):
            if len(segments) == 1:
                # Waiting for more line
                return None
            tokens = segments[0]
            for seg in segments[1:]:
                tokens = tokens + '\n' + seg
                if seg.endswith("$$"):
                    # Keep left
                    self.last_commit = self.last_commit + \
                                           self.uncommitted_msg[:len(tokens) + self.uncommitted_msg.find(tokens)]
                    return tokens
            return None
        elif segments[0].startswith("* "):
            if segments[-1] == '' or segments[-1].startswith("*"):
                return None
            self.last_commit = msg.removesuffix(segments[-1])
            return self.uncommitted_msg.removesuffix(segments[-1]).strip()
        elif self.uncommitted_msg[-1] == '\n':
            self.last_commit = msg
            # logger.debug("直接发送消息：" + '\n'.join(segments).strip())
            return '\n'.join(segments).strip()
        return None

    async def result(self) -> str:
        return self.uncommitted_msg

    async def __aenter__(self) -> None:
        self.msg = ''

    async def __aexit__(self, exc_type: type[BaseException], exc: BaseException, tb) -> None:
        self.msg = None
