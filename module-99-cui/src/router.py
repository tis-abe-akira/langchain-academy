from dotenv import load_dotenv
load_dotenv()
##
# Review
# 
# メッセージを状態として使用し、ツールがバインドされたチャットモデルを使用するグラフを構築しました。
# グラフが以下のことができることを確認しました:
# - ツール呼び出しを返す
# - 自然言語の応答を返す
#
# Goals
#
# これはルーターのようなもので、チャットモデルがユーザー入力に基づいて直接応答するかツールを呼び出すかをルーティングします。
# これはエージェントの簡単な例であり、LLMがツールを呼び出すか直接応答するかによって制御フローを指示しています。

# グラフを拡張して、どちらの出力にも対応できるようにしましょう！
# これには、次の2つのアイデアを使用できます:
# (1) ツールを呼び出すノードを追加する。
# (2) チャットモデルの出力を確認し、ツール呼び出しノードにルーティングするか、ツール呼び出しが行われない場合は単に終了する条件付きエッジを追加する。
##

import os, getpass

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("OPENAI_API_KEY")

from langchain_openai import ChatOpenAI

def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b

llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools([multiply])

# 組み込みのToolNodeを使用し、ツールのリストを渡して初期化します。
# 組み込みのtools_conditionを条件付きエッジとして使用します。
from IPython.display import Image, display
from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition

# Node
def tool_calling_llm(state: MessagesState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Build graph
builder = StateGraph(MessagesState)
builder.add_node("tool_calling_llm", tool_calling_llm)
builder.add_node("tools", ToolNode([multiply]))
builder.add_edge(START, "tool_calling_llm")
builder.add_conditional_edges(
    "tool_calling_llm",
    # 最新のメッセージ（結果）がアシスタントからのツール呼び出しである場合 -> tools_conditionはtoolsにルーティングします
    # 最新のメッセージ（結果）がアシスタントからのツール呼び出しでない場合 -> tools_conditionはENDにルーティングします
    tools_condition,
)
builder.add_edge("tools", END)
graph = builder.compile()

# View
from utils import save_mermaid_to_html
# display(Image(graph.get_graph().draw_mermaid_png()))
save_mermaid_to_html(graph.get_graph().draw_mermaid(), "out/router.html")

## 実行！
from langchain_core.messages import HumanMessage
# messages = [HumanMessage(content="How can I get LangChain module?")]
messages = [HumanMessage(content="multiply 4 and 2")]
messages = graph.invoke({"messages": messages})
for m in messages['messages']:
    m.pretty_print()
