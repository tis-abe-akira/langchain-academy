from dotenv import load_dotenv
load_dotenv()

"""
Goals

さて、これを汎用エージェントアーキテクチャに拡張できます。
上記のルーターでは、モデルを呼び出し、ツールを呼び出すことを選択した場合、ユーザーにToolMessageを返しました。
しかし、そのToolMessageを単にモデルに渡したらどうなるでしょうか？
モデルに(1)別のツールを呼び出すか(2)直接応答するかを任せることができます。
これがReActの直感であり、汎用エージェントアーキテクチャです。
- act - モデルに特定のツールを呼び出させる
- observe - ツールの出力をモデルに渡す
- reason - モデルにツールの出力を基に次に何をするか（例: 別のツールを呼び出すか、直接応答するか）を判断させる
この汎用アーキテクチャは、多くの種類のツールに適用できます。
"""
from langchain_openai import ChatOpenAI

def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b

# This will be a tool
def add(a: int, b: int) -> int:
    """Adds a and b.

    Args:
        a: first int
        b: second int
    """
    return a + b

def divide(a: int, b: int) -> float:
    """Divide a and b.

    Args:
        a: first int
        b: second int
    """
    return a / b

tools = [add, multiply, divide]
llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools(tools)


# LLMを作成し、全体的に望ましいエージェントの動作をプロンプトしましょう。
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage

# System message
sys_msg = SystemMessage(content="You are a helpful assistant tasked with performing arithmetic on a set of inputs.")

# Node
def assistant(state: MessagesState):
   return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

"""
以前と同様に、MessagesStateを使用し、ツールのリストを持つToolsノードを定義します。
Assistantノードは、ツールがバインドされたモデルです。
AssistantノードとToolsノードでグラフを作成します。
tools_conditionエッジを追加し、Assistantがツールを呼び出すかどうかに基づいてEndまたはToolsにルーティングします。
ここで、新しいステップを1つ追加します:
ToolsノードをAssistantに戻してループを形成します。
- Assistantノードが実行された後、tools_conditionがモデルの出力がツール呼び出しかどうかを確認します。
- もしツール呼び出しであれば、フローはToolsノードに向かいます。
- ToolsノードはAssistantに戻ります。
- モデルがツールを呼び出す限り、このループは続きます。
- モデルの応答がツール呼び出しでない場合、フローはENDに向かい、プロセスが終了します。
"""
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
from IPython.display import Image, display

# Graph
builder = StateGraph(MessagesState)

# Define nodes: these do the work
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))

# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
builder.add_edge("tools", "assistant")
react_graph = builder.compile()

from utils import save_mermaid_to_html
# display(Image(graph.get_graph().draw_mermaid_png()))
save_mermaid_to_html(react_graph.get_graph().draw_mermaid(), "out/agent.html")


# Agent実行
messages = [HumanMessage(content="Add 3 and 4. Multiply the output by 2. Divide the output by 5")]
messages = react_graph.invoke({"messages": messages})

for m in messages['messages']:
    m.pretty_print()
