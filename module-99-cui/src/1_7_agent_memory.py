from dotenv import load_dotenv
load_dotenv()

"""
Review

以前、次のことができるエージェントを構築しました:
- 行動 - モデルに特定のツールを呼び出させる
- 観察 - ツールの出力をモデルに渡す
- 推論 - モデルにツールの出力を基に次に何をするか（例: 別のツールを呼び出すか、直接応答するか）を判断させる

Goals
さて、メモリを導入してエージェントを拡張します。
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

from langgraph.graph import MessagesState
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# System message
sys_msg = SystemMessage(content="You are a helpful assistant tasked with performing arithmetic on a set of inputs.")

# Node
def assistant(state: MessagesState):
   return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition, ToolNode
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

# View
from utils import save_mermaid_to_html
save_mermaid_to_html(react_graph.get_graph().draw_mermaid(), "out/agent_memory.html")


"""
Memory
Let's run our agent, as before.
"""

messages = [HumanMessage(content="Add 3 and 4.")]
messages = react_graph.invoke({"messages": messages})
for m in messages['messages']:
    m.pretty_print()

# Now, let's multiply by 2!
messages = [HumanMessage(content="Multiply that by 2.")]
messages = react_graph.invoke({"messages": messages})
for m in messages['messages']:
    m.pretty_print()


"""
最初のチャットで7の記憶を保持していません！
これは、状態が単一のグラフ実行に対して一時的だからです。
もちろん、これでは中断を含むマルチターンの会話を行う能力が制限されます。
これに対処するために永続性を使用できます！
LangGraphは、各ステップの後にグラフの状態を自動的に保存するチェックポインタを使用できます。
この組み込みの永続化レイヤーはメモリを提供し、LangGraphが最後の状態更新から再開できるようにします。
最も簡単に使用できるチェックポインタの一つはMemorySaverで、グラフの状態を保存するインメモリのキー・バリュー・ストアです。
必要なのは、チェックポインタを使ってグラフをコンパイルするだけで、グラフにメモリが追加されます！
"""
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
react_graph_memory = builder.compile(checkpointer=memory)

"""
メモリを使用する場合、thread_idを指定する必要があります。
このthread_idは、グラフ状態のコレクションを保存します。
ここに簡単な説明があります:
- チェックポインタはグラフの各ステップで状態を書き込みます
- これらのチェックポイントはスレッドに保存されます
- 将来的にそのスレッドにアクセスするためにはthread_idを使用します
"""
# Specify a thread
config = {"configurable": {"thread_id": "1"}}

# Specify an input
messages = [HumanMessage(content="Add 3 and 4.")]

# Run
messages = react_graph_memory.invoke({"messages": messages},config)
for m in messages['messages']:
    m.pretty_print()

"""
同じthread_idを渡すと、以前に記録された状態のチェックポイントから続行できます！
この場合、上記の会話がスレッドに記録されます。
渡したHumanMessage（「それを2倍にしてください。」）は上記の会話に追加されます。
したがって、モデルは「それ」が「3と4の合計は7である」ことを指していることを認識します。
"""
messages = [HumanMessage(content="Multiply that by 2.")]
messages = react_graph_memory.invoke({"messages": messages}, config)
for m in messages['messages']:
    m.pretty_print()
