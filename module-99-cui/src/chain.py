from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI

##
# メッセージ
#
# チャットモデルは会話内の異なる役割をキャプチャするメッセージを使用できます。
# LangChainは、HumanMessage、AIMessage、SystemMessage、ToolMessageなど、さまざまなメッセージタイプをサポートしています。
# これらは、ユーザーからのメッセージ、チャットモデルからのメッセージ、チャットモデルに行動を指示するためのメッセージ、およびツール呼び出しからのメッセージを表します。
# メッセージのリストを作成しましょう。
# 各メッセージにはいくつかの要素を指定できます:
# - content - メッセージの内容
# - name - 任意で、メッセージの作成者
# - response_metadata - 任意で、メタデータの辞書（例: AIMessagesの場合、モデルプロバイダーによってよく設定される）
##

from pprint import pprint
from langchain_core.messages import AIMessage, HumanMessage

messages = [AIMessage(content=f"So you said you were researching ocean mammals?", name="Model")]
messages.append(HumanMessage(content=f"Yes, that's right.",name="Lance"))
messages.append(AIMessage(content=f"Great, what would you like to learn about.", name="Model"))
messages.append(HumanMessage(content=f"I want to learn about the best place to see Orcas in the US. Describe in Japanese Language", name="Lance"))

for m in messages:
    m.pretty_print()

##
# Chat Models
#
# チャットモデルは、上記で説明したように、メッセージのシーケンスを入力として使用し、メッセージタイプをサポートできます。
# 選択肢はたくさんあります！OpenAIを使ってみましょう。
# OPENAI_API_KEYが設定されているか確認し、設定されていない場合は入力を求められます。
# チャットモデルをロードし、メッセージのリストで呼び出すことができます。
# 結果が特定のresponse_metadataを持つAIMessageであることがわかります。
##
import os, getpass

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("OPENAI_API_KEY")

from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o")
result = llm.invoke(messages)
print(f"戻り値の型: {type(result)}")

print("\nResult: ")
result.pretty_print()

# response_metadataを表示する
print(f"\nResponse Metadata: {result.response_metadata}")

## 
# Tools
#
# ツールは、モデルが外部システムと対話する際に役立ちます。
# 外部システム（例: API）は、自然言語ではなく特定の入力スキーマやペイロードを必要とすることがよくあります。
# 例えば、APIをツールとしてバインドするとき、モデルに必要な入力スキーマを認識させます。
# モデルはユーザーからの自然言語入力に基づいてツールを呼び出すことを選択します。
# そして、ツールのスキーマに従った出力を返します。
# 多くのLLMプロバイダーはツール呼び出しをサポートしており、LangChainのツール呼び出しインターフェースはシンプルです。
# 任意のPython関数を単に渡すことができます。 ChatModel.bind_tools(function).
#
# ツール呼び出しの簡単な例を紹介しましょう！
# multiply関数が私たちのツールです。
##
def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: first int
        b: second int
    """
    return a * b

# ツールをバインドする。
llm_with_tools = llm.bind_tools([multiply])

# 入力を渡すと - 例えば、「2かける3は何ですか」 - ツール呼び出しが返されるのがわかります。
# ツール呼び出しには、呼び出す関数の名前とともに、関数の入力スキーマに一致する特定の引数が含まれています。
tool_call = llm_with_tools.invoke([HumanMessage(content=f"What is 2 multiplied by 3", name="Lance")])
print(f"\ntool_call: {tool_call}")

##
# Using messages as state
#
# これらの基礎が整ったので、グラフ状態(graph state)でメッセージを使用できます。
# 状態をMessagesStateとして定義しましょう。これは、単一のキーmessagesを持つTypedDictです。
# messagesは、上記で定義したメッセージ（例: HumanMessageなど）のリストです。
##
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage

class MessagesState(TypedDict):
    messages: list[AnyMessage]


##
# Reducers
#
# ここで、少し問題があります！
# 先ほど話したように、各ノードは状態キーmessagesに新しい値を返します。
# しかし、この新しい値は以前のmessagesの値を上書きしてしまいます。
# グラフが実行されるとき、messagesをmessages状態キーに追加したいです。
# これを解決するためにリデューサー関数を使用できます。
# リデューサーは、状態の更新方法を指定することができます。
# リデューサー関数が指定されていない場合、キーの更新は前述のように上書きされると見なされます。
# しかし、messagesを追加するために、事前に構築されたadd_messagesリデューサーを使用できます。
# これにより、任意のmessagesが既存のmessagesリストに追加されることが保証されます。
# 単にmessagesキーをadd_messagesリデューサー関数でメタデータとして注釈するだけです。
##
from typing import Annotated
from langgraph.graph.message import add_messages

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

# グラフ状態でメッセージのリストを持つことは非常に一般的なので、LangGraphには事前に構築されたMessagesStateがあります！
# MessagesStateは次のように定義されています:
# - 事前に構築された単一のmessagesキーを持つ
# - これはAnyMessageオブジェクトのリストです
# - add_messagesリデューサーを使用します
# 通常、上記のようにカスタムTypedDictを定義するよりも冗長でないため、MessagesStateを使用します。
from langgraph.graph import MessagesState

class MessagesState(MessagesState):
    # Add any keys needed beyond messages, which is pre-built 
    pass

# もう少し深く掘り下げて、`add_messages`リデューサーが単独でどのように機能するかを見てみましょう。
# Initial state
initial_messages = [AIMessage(content="Hello! How can I assist you?", name="Model"),
                    HumanMessage(content="I'm looking for information on marine biology.", name="Lance")
                   ]

# New message to add
new_message = AIMessage(content="Sure, I can help with that. What specifically are you interested in?", name="Model")

# Test
added_messages = add_messages(initial_messages , new_message)

print(f"\nAdded messages: {added_messages}")


##
# Our graph
# では、MessagesStateをグラフで使用してみましょう。
##
from IPython.display import Image, display
from langgraph.graph import StateGraph, START, END
    
# Node
def tool_calling_llm(state: MessagesState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Build graph
builder = StateGraph(MessagesState)
builder.add_node("tool_calling_llm", tool_calling_llm)
builder.add_edge(START, "tool_calling_llm")
builder.add_edge("tool_calling_llm", END)
graph = builder.compile()

# View
from utils import save_mermaid_to_html
# display(Image(graph.get_graph().draw_mermaid_png()))
save_mermaid_to_html(graph.get_graph().draw_mermaid(), "out/chain.html")

# Hello! と入力すると、LLMはツール呼び出しなしで応答します。
messages = graph.invoke({"messages": HumanMessage(content="Hello!")})
for m in messages['messages']:
    m.pretty_print()

# LLMは、入力やタスクがそのツールによって提供される機能を必要とすると判断した場合にツールを使用することを選択します。
messages = graph.invoke({"messages": HumanMessage(content="Multiply 2 and 3!")})

# メッセージをループして表示
for m in messages['messages']:
    m.pretty_print()

    # デバッグ用にmオブジェクトの属性を表示
    # print("Attributes of m:", dir(m))

    # ツール呼び出しの結果を表示（GitHub Copilot Chatにてコード生成）
    # TODO: 次のRouterのところできちんとツールの実行に対応する。ここでは強引に呼び出しをしているだけ。
    if hasattr(m, 'tool_calls'):
        for call in m.tool_calls:
            print("Tool Call:", call)
            # ツールの呼び出しを実行
            if 'name' in call and 'args' in call:
                tool_name = call['name']
                tool_args = call['args']
                if tool_name == 'multiply':
                    result = multiply(**tool_args)
                    print("Tool Result:", result)
                else:
                    print(f"Unknown tool: {tool_name}")
            else:
                print("Invalid tool call format.")
    else:
        print("No tool_calls attribute found.")

