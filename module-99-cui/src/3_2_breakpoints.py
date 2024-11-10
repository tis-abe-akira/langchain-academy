from dotenv import load_dotenv
load_dotenv()

"""
復習

「人間がループの中に入る」には、グラフの実行中にその出力を確認したいことがよくあります。
ストリーミングによって、そのための基礎を築きました。

目標
それでは、「人間がループの中に入る」ための動機について説明します。
(1) 承認 - エージェントを中断し、ユーザーに状態を提示して、ユーザーがアクションを承認できるようにします。
(2) デバッグ - グラフを巻き戻して、問題を再現または回避できます。
(3) 編集 - 状態を変更できます。
LangGraphは、さまざまな「人間がループの中に入る」ワークフローをサポートするために、エージェントの状態を取得または更新するいくつかの方法を提供しています。
まず、ブレークポイントを紹介します。これは、特定のステップでグラフを停止するための簡単な方法です。
ユーザーの承認を有効にする方法を示します。
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
    """Adds a and b.

    Args:
        a: first int
        b: second int
    """
    return a / b

tools = [add, multiply, divide]
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools(tools)

# Graphの構築
# from IPython.display import Image, display

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition, ToolNode

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# System message
sys_msg = SystemMessage(content="You are a helpful assistant tasked with performing arithmetic on a set of inputs.")

# Node
def assistant(state: MessagesState):
   return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

# Graph
builder = StateGraph(MessagesState)

# Define nodes: these do the work
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))

# Define edges: these determine the control flow
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
    # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
    tools_condition,
)
builder.add_edge("tools", "assistant")

memory = MemorySaver()

# interrupt_before=["tools"]が付与されていることに着目！
graph = builder.compile(interrupt_before=["tools"], checkpointer=memory)

# Show
# display(Image(graph.get_graph(xray=True).draw_mermaid_png()))

"""
それでは、ユーザー入力を受け入れる具体的なユーザー承認ステップとこれらを組み合わせましょう。
"""
# Input
initial_input = {"messages": HumanMessage(content="Multiply 2 and 3")}

# Thread
thread = {"configurable": {"thread_id": "2"}}

# Run the graph until the first interruption
for event in graph.stream(initial_input, thread, stream_mode="values"):
    event['messages'][-1].pretty_print()

# Get user feedback
user_approval = input("Do you want to call the tool? (yes/no): ")

# Check approval
if user_approval.lower() == "yes":

    # If approved, continue the graph execution (If approved, continue the graph execution)
    for event in graph.stream(None, thread, stream_mode="values"):
        event['messages'][-1].pretty_print()

else:
    print("Operation cancelled by user.")


