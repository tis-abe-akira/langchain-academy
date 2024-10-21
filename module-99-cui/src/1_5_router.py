from langchain_core.messages import HumanMessage
from utils import save_mermaid_to_html
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, START, END
from IPython.display import Image, display
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()

"""
Goals

これはルーターのようなもので、チャットモデルがユーザー入力に基づいて直接応答するかツール呼び出しを行うかをルーティングします。
これはエージェントの簡単な例であり、LLMがツールを呼び出すか直接応答するかによって制御フローを指示しています。

これには、次の2つのアイデアを使用できます：
(1) ツールを呼び出すノードを追加する。
(2) チャットモデルの出力を確認し、ツール呼び出しノードにルーティングするか、ツール呼び出しが行われない場合は単に終了する条件付きエッジを追加する。
"""
def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b

llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools([multiply])

"""
組み込みのToolNodeを使用し、ツールのリストを渡して初期化します。
組み込みのtools_conditionを条件付きエッジとして使用します。
"""

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
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
builder.add_edge("tools", END)
graph = builder.compile()

# View
# display(Image(graph.get_graph().draw_mermaid_png()))
save_mermaid_to_html(graph.get_graph().draw_mermaid(), "out/router.html")

# run 
# messages = [HumanMessage(content="Hello world.")]
messages = [HumanMessage(content="300 かける 578 はいくつですか？")]
messages = graph.invoke({"messages": messages})
for m in messages['messages']:
    m.pretty_print()
