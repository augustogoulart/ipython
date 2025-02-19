"""
This is an example of Fake LLM Completer for IPython 
8.32 – this is provisional and may change.

To test this you can run the following command from the root of IPython 
directory:

    $ ipython --TerminalInteractiveShell.llm_provider_class=examples.auto_suggest_llm.ExampleCompletionProvider

Or you can set the value in your config file

    c.TerminalInteractiveShell.llm_provider_class="fully.qualified.name.ToYourCompleter"

And at runtime bing for example `ctrl-q` to triger autosugges:

    In [1]: from examples.auto_suggest_llm import setup_shortcut
       ...: setup_shortcut('c-q')


"""

import asyncio
import textwrap
from asyncio import FIRST_COMPLETED, Task, create_task, wait
from typing import Any, AsyncIterable, AsyncIterator, Collection, TypeVar

from jupyter_ai.completions.models import (
    InlineCompletionList,
    InlineCompletionReply,
    InlineCompletionRequest,
    InlineCompletionStreamChunk,
)
from jupyter_ai_magics import BaseProvider
from langchain_community.llms import FakeListLLM


from IPython.terminal.shortcuts import Binding
from IPython.terminal.shortcuts.filters import (
    navigable_suggestions,
    default_buffer_focused,
)
from IPython.terminal.shortcuts.auto_suggest import llm_autosuggestion


def setup_shortcut(seq):
    import IPython

    ip = IPython.get_ipython()
    ip.pt_app.key_bindings.add_binding(
        seq, filter=(navigable_suggestions & default_buffer_focused)
    )(llm_autosuggestion),


class ExampleCompletionProvider(BaseProvider, FakeListLLM):  # type: ignore[misc, valid-type]
    """
    This is an example Fake LLM provider for IPython

    As of 8.32 this is provisional and may change without any warnings
    """

    id = "my_provider"
    name = "My Provider"
    model_id_key = "model"
    models = ["model_a"]

    def __init__(self, **kwargs: Any):
        kwargs["responses"] = ["This fake response will not be used for completion"]
        kwargs["model_id"] = "model_a"
        super().__init__(**kwargs)

    async def generate_inline_completions(
        self, request: InlineCompletionRequest
    ) -> InlineCompletionReply:
        raise ValueError("IPython 8.32 only support streaming models for now.")

    async def stream_inline_completions(
        self, request: InlineCompletionRequest
    ) -> AsyncIterator[InlineCompletionStreamChunk]:
        token_1 = f"t{request.number}s0"

        yield InlineCompletionReply(
            list=InlineCompletionList(
                items=[
                    {"insertText": "It", "isIncomplete": True, "token": token_1},
                ]
            ),
            reply_to=request.number,
        )

        reply: InlineCompletionStreamChunk
        async for reply in self._stream(
            textwrap.dedent(
                """
                was then that the fox appeared.
                “Good morning,” said the fox.
                “Good morning,” the little prince responded politely, although when he turned around he saw nothing.
                “I am right here,” the voice said, “under the apple tree.”
                “Who are you?” asked the little prince, and added, “You are very pretty to look at.”
                “I am a fox,” said the fox.
                “Come and play with me,” proposed the little prince. “I am so unhappy.”
                """
            ).strip(),
            request.number,
            token_1,
            start_with="It",
        ):
            yield reply

    async def _stream(
        self, sentence: str, request_number: int, token: str, start_with: str = ""
    ) -> AsyncIterable[InlineCompletionStreamChunk]:
        suggestion = start_with

        for fragment in sentence.split(" "):
            await asyncio.sleep(0.05)
            suggestion += " " + fragment
            yield InlineCompletionStreamChunk(
                type="stream",
                response={"insertText": suggestion, "token": token},
                reply_to=request_number,
                done=False,
            )

        # finally, send a message confirming that we are done
        yield InlineCompletionStreamChunk(
            type="stream",
            response={"insertText": suggestion, "token": token},
            reply_to=request_number,
            done=True,
        )
