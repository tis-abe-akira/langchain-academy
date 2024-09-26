from dotenv import load_dotenv
load_dotenv()

##
# Review
# TypedDict、Pydantic、またはデータクラスを含む、LangGraphの状態スキーマを定義するいくつかの異なる方法を説明しました。
#
# Goals
# さて、リデューサーについて詳しく見ていきます。リデューサーは、状態スキーマ内の特定のキー/チャネルに対して状態更新がどのように行われるかを指定します。

# Default overwriting state
# 状態スキーマとして`TypedDict`を使用しましょう。
from typing_extensions import TypedDict
from IPython.display import Image, display
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    foo: int

def node_1(state):
    print("---Node 1---")
    return {"foo": state['foo'] + 1}

# Build graph
builder = StateGraph(State)
builder.add_node("node_1", node_1)

# Logic
builder.add_edge(START, "node_1")
builder.add_edge("node_1", END)

# Add
graph = builder.compile()

# View
from utils import save_mermaid_to_html
save_mermaid_to_html(graph.get_graph().draw_mermaid(), "out/2_2_state_reducers.html")

result = graph.invoke({"foo" : 1})
print(result)

# 状態更新を見てみましょう。{"foo": state['foo'] + 1}を返します。
# 前述のように、デフォルトではLangGraphは状態を更新するための推奨方法を知りません。
# そのため、node_1のfooの値を単に上書きします：
# return {"foo": state['foo'] + 1}
# {'foo': 1}を入力として渡すと、グラフから返される状態は{'foo': 2}です。
#
# Branching
# ノードが分岐するケースを見てみましょう。

class State(TypedDict):
    foo: int

def node_1(state):
    print("---Node 1---")
    return {"foo": state['foo'] + 1}

def node_2(state):
    print("---Node 2---")
    return {"foo": state['foo'] + 1}

def node_3(state):
    print("---Node 3---")
    return {"foo": state['foo'] + 1}

# Build graph
builder = StateGraph(State)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)

# Logic
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_1", "node_3")
builder.add_edge("node_2", END)
builder.add_edge("node_3", END)

# Add
graph = builder.compile()

# View
from utils import save_mermaid_to_html
save_mermaid_to_html(graph.get_graph().draw_mermaid(), "out/2_2_state_reducers-2.html")

from langgraph.errors import InvalidUpdateError
try:
    graph.invoke({"foo" : 1})
except InvalidUpdateError as e:
    print(f"InvalidUpdateError occurred: {e}")

# 問題が発生しました！
# ノード1がノード2とノード3に分岐しています。
# ノード2とノード3は並行して実行されるため、グラフの同じステップで実行されます。
# 両方が同じステップ内で状態を上書きしようとします。
# これはグラフにとって曖昧です！どの状態を保持すべきでしょうか？

# Reducers
#
# リデューサーはこの問題に対処するための一般的な方法を提供します。
# リデューサーは更新の方法を指定します。
# Annotated型を使用してリデューサー関数を指定できます。
# 例えば、この場合、上書きするのではなく、各ノードから返される値を追加してみましょう。
# これを実行できるリデューサーが必要です：operator.addはPythonの組み込みoperatorモジュールの関数です。
# operator.addをリストに適用すると、リストの連結が行われます。
from operator import add
from typing import Annotated

class State(TypedDict):
    foo: Annotated[list[int], add]

def node_1(state):
    print("---Node 1---")
    return {"foo": [state['foo'][0] + 1]}

# Build graph
builder = StateGraph(State)
builder.add_node("node_1", node_1)

# Logic
builder.add_edge(START, "node_1")
builder.add_edge("node_1", END)

# Add
graph = builder.compile()

# View
from utils import save_mermaid_to_html
save_mermaid_to_html(graph.get_graph().draw_mermaid(), "out/2_2_state_reducers-3.html")

result = graph.invoke({"foo" : [1]})
print(result)

# これで、状態キーfooはリストになります。
# このoperator.addリデューサー関数は、各ノードからの更新をこのリストに追加します。
def node_1(state):
    print("---Node 1---")
    return {"foo": [state['foo'][-1] + 1]}

def node_2(state):
    print("---Node 2---")
    return {"foo": [state['foo'][-1] + 1]}

def node_3(state):
    print("---Node 3---")
    return {"foo": [state['foo'][-1] + 1]}

# Build graph
builder = StateGraph(State)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)

# Logic
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_1", "node_3")
builder.add_edge("node_2", END)
builder.add_edge("node_3", END)

# Add
graph = builder.compile()

# View
from utils import save_mermaid_to_html
save_mermaid_to_html(graph.get_graph().draw_mermaid(), "out/2_2_state_reducers-4.html")

# ノード2とノード3での更新は、同じステップ内で並行して実行されることがわかります。
result = graph.invoke({"foo" : [1]})
print(result)

# では、fooにNoneを渡した場合に何が起こるか見てみましょう。
# リデューサーのoperator.addが、node_1でリストにNoneTypeを連結しようとするため、エラーが発生します。
try:
    graph.invoke({"foo" : None})
except TypeError as e:
    print(f"TypeError occurred: {e}")

# Custom Reducers
#
# このようなケースに対処するために、カスタムリデューサーを定義することもできます。
# 例えば、リストを結合し、入力のいずれかまたは両方がNoneである場合を処理するカスタムリデューサーロジックを定義してみましょう。
def reduce_list(left: list | None, right: list | None) -> list:
    """Safely combine two lists, handling cases where either or both inputs might be None.

    Args:
        left (list | None): The first list to combine, or None.
        right (list | None): The second list to combine, or None.

    Returns:
        list: A new list containing all elements from both input lists.
               If an input is None, it's treated as an empty list.
    """
    if not left:
        left = []
    if not right:
        right = []
    return left + right

class DefaultState(TypedDict):
    foo: Annotated[list[int], add]

class CustomReducerState(TypedDict):
    foo: Annotated[list[int], reduce_list]

# node_1では、値2を追加します。
def node_1(state):
    print("---Node 1---")
    return {"foo": [2]}

# Build graph
builder = StateGraph(DefaultState)
builder.add_node("node_1", node_1)

# Logic
builder.add_edge(START, "node_1")
builder.add_edge("node_1", END)

# Add
graph = builder.compile()

# View
from utils import save_mermaid_to_html
save_mermaid_to_html(graph.get_graph().draw_mermaid(), "out/2_2_state_reducers-5.html")

try:
    print(graph.invoke({"foo" : None}))
except TypeError as e:
    print(f"TypeError occurred: {e}")

# では、カスタムリデューサーを使ってみましょう。エラーが発生しないことがわかります。

# Build graph
builder = StateGraph(CustomReducerState)
builder.add_node("node_1", node_1)

# Logic
builder.add_edge(START, "node_1")
builder.add_edge("node_1", END)

# Add
graph = builder.compile()

# View
save_mermaid_to_html(graph.get_graph().draw_mermaid(), "out/2_2_state_reducers-6.html")

try:
    print(graph.invoke({"foo" : None}))
except TypeError as e:
    print(f"TypeError occurred: {e}")


##
# Messages
# 
# モジュール1では、組み込みのリデューサーadd_messagesを使用して状態内のメッセージを処理する方法を示しました。
# また、メッセージを操作したい場合に便利なショートカットとしてMessagesStateがあることも示しました。
# - MessagesStateには組み込みのmessagesキーがあります
# - また、このキーのための組み込みのadd_messagesリデューサーもあります
# これら二つは同等です。
# 簡潔にするために、langgraph.graphからMessagesStateクラスを使用します。

from typing import Annotated
from langgraph.graph import MessagesState
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

# Define a custom TypedDict that includes a list of messages with add_messages reducer
class CustomMessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    added_key_1: str
    added_key_2: str
    # etc

# Use MessagesState, which includes the messages key with add_messages reducer
class ExtendedMessagesState(MessagesState):
    # Add any keys needed beyond messages, which is pre-built 
    added_key_1: str
    added_key_2: str
    # etc

# Let's talk a bit more about usage of the add_messages reducer.

from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, HumanMessage

# Initial state
initial_messages = [AIMessage(content="Hello! How can I assist you?", name="Model"),
                    HumanMessage(content="I'm looking for information on marine biology.", name="Lance")
                   ]

# New message to add
new_message = AIMessage(content="Sure, I can help with that. What specifically are you interested in?", name="Model")

# Test
result = add_messages(initial_messages , new_message)
print(result)


# add_messagesを使用すると、状態内のmessagesキーにメッセージを追加できることがわかります。

# Re-writing
#
# add_messagesリデューサーを使用する際の便利なトリックをいくつか紹介します。
# メッセージリスト内の既存のメッセージと同じIDを持つメッセージを渡すと、そのメッセージは上書きされます！
# Initial state
initial_messages = [AIMessage(content="Hello! How can I assist you?", name="Model", id="1"),
                    HumanMessage(content="I'm looking for information on marine biology.", name="Lance", id="2")
                   ]

# New message to add
new_message = HumanMessage(content="I'm looking for information on whales, specifically", name="Lance", id="2")

# Test
print(add_messages(initial_messages , new_message))

# Removal
#
# add_messagesはメッセージの削除も可能にします。
# これには、langchain_coreからRemoveMessageを使用します。
from langchain_core.messages import RemoveMessage

# Message list
messages = [AIMessage("Hi.", name="Bot", id="1")]
messages.append(HumanMessage("Hi.", name="Lance", id="2"))
messages.append(AIMessage("So you said you were researching ocean mammals?", name="Bot", id="3"))
messages.append(HumanMessage("Yes, I know about whales. But what others should I learn about?", name="Lance", id="4"))

# Isolate messages to delete
delete_messages = [RemoveMessage(id=m.id) for m in messages[:-2]]
print(delete_messages)

print(add_messages(messages, delete_messages))

# delete_messagesで指定されたメッセージID 1と2がリデューサーによって削除されることがわかります。
# これが実際にどのように機能するかは、後ほど確認します。
