from dotenv import load_dotenv
load_dotenv()

"""
Review

モジュール1では基礎を築きました！以下のことができるエージェントを構築しました：
- 行動する - モデルが特定のツールを呼び出せるようにする
- 観察する - ツールの出力をモデルに渡す
- 推論する - モデルがツールの出力について推論し、次に何をするか（例：別のツールを呼び出すか、直接応答するか）を決定できるようにする
- 状態を保持する - メモリ内チェックポインタを使用して、中断を伴う長時間の会話をサポートする
そして、LangGraph Studioでローカルに提供する方法や、LangGraph Cloudでデプロイする方法を示しました。

Goals
このモジュールでは、状態とメモリの両方についてより深く理解していきます。
まず、状態スキーマを定義するいくつかの異なる方法を見てみましょう。
"""

"""
Schema

LangGraphのStateGraphを定義する際には、状態スキーマを使用します。
状態スキーマは、グラフが使用するデータの構造と型を表します。
すべてのノードはそのスキーマと通信することが期待されます。
LangGraphは、さまざまなPythonの型や検証アプローチに対応する柔軟性を提供します！

TypedDict
モジュール1で述べたように、PythonのtypingモジュールからTypedDictクラスを使用できます。
これにより、キーとそれに対応する値の型を指定できます。
ただし、これらは型ヒントであることに注意してください。
静的型チェッカー（例えばmypy）やIDEによって、コード実行前に型関連のエラーを検出するために使用されます。
しかし、実行時には強制されません！
"""

from typing_extensions import TypedDict

class TypedDictState(TypedDict):
    foo: str
    bar: str

"""
より具体的な値の制約を設けるために、Literal型ヒントを使用できます。
ここでは、moodは「happy」または「sad」のどちらかのみです。
"""
from typing import Literal

class TypedDictState(TypedDict):
    name: str
    mood: Literal["happy","sad"]

"""
定義した状態クラス（例えば、ここではTypedDictState）をLangGraphで使用するには、単にそれをStateGraphに渡すだけです。
そして、各状態キーをグラフ内の「チャネル」として考えることができます。
モジュール1で説明したように、各ノードで指定されたキーまたは「チャネル」の値を上書きします。
"""
import random
from IPython.display import Image, display
from langgraph.graph import StateGraph, START, END

def node_1(state):
    print("---Node 1---")
    return {"name": state['name'] + " is ... "}

def node_2(state):
    print("---Node 2---")
    return {"mood": "happy"}

def node_3(state):
    print("---Node 3---")
    return {"mood": "sad"}

def decide_mood(state) -> Literal["node_2", "node_3"]:
        
    # Here, let's just do a 50 / 50 split between nodes 2, 3
    if random.random() < 0.5:

        # 50% of the time, we return Node 2
        return "node_2"
    
    # 50% of the time, we return Node 3
    return "node_3"

# Build graph
builder = StateGraph(TypedDictState)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)

# Logic
builder.add_edge(START, "node_1")
builder.add_conditional_edges("node_1", decide_mood)
builder.add_edge("node_2", END)
builder.add_edge("node_3", END)

# Add
graph = builder.compile()

# View
from utils import save_mermaid_to_html
save_mermaid_to_html(graph.get_graph().draw_mermaid(), "out/2_1_state_schema.html")

# 状態が辞書であるため、グラフを辞書で呼び出して、状態の`name`キーの初期値を設定するだけです。
result = graph.invoke({"name":"Lance"})
print(result)


"""
Dataclass
Pythonのデータクラスは、構造化データを定義する別の方法を提供します。
データクラスは、主にデータを格納するために使用されるクラスを簡潔な構文で作成する手段を提供します。
"""
from dataclasses import dataclass

@dataclass
class DataclassState:
    name: str
    mood: Literal["happy","sad"]

"""
データクラスのキーにアクセスするには、node_1で使用される添字を変更するだけです：
- 上記のTypedDictのstate["name"]ではなく、データクラスのstate.nameを使用します
少し奇妙に感じるかもしれませんが、各ノードで状態更新を行うために辞書を返すことができます。
これは、LangGraphが状態オブジェクトの各キーを個別に保存するためです。
ノードから返されるオブジェクトは、状態内のキー（属性）と一致するキーを持っているだけで十分です！
この場合、データクラスにはキーnameがあるので、stateがTypedDictであったときと同様に、ノードから辞書を渡して更新できます。
"""
def node_1(state):
    print("---Node 1---")
    return {"name": state.name + " is ... "}

# Build graph
builder = StateGraph(DataclassState)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)

# Logic
builder.add_edge(START, "node_1")
builder.add_conditional_edges("node_1", decide_mood)
builder.add_edge("node_2", END)
builder.add_edge("node_3", END)

# Add
graph = builder.compile()

# View
from utils import save_mermaid_to_html
save_mermaid_to_html(graph.get_graph().draw_mermaid(), "out/2_1_state_schema-2.html")

# データクラスを使用して、状態内の各キー/チャネルの初期値を設定します！
result = graph.invoke(DataclassState(name="Lance",mood="sad"))
print(result)


"""
Pydantic
前述のように、TypedDictとデータクラスは型ヒントを提供しますが、実行時には型を強制しません。
これは、エラーを発生させずに無効な値を割り当てる可能性があることを意味します！
例えば、型ヒントでmood: list[Literal["happy","sad"]]と指定しているにもかかわらず、moodにmadを設定することができます。
"""
dataclass_instance = DataclassState(name="Lance", mood="mad")

"""
Pydanticは、Pythonの型アノテーションを使用したデータ検証と設定管理のライブラリです。
その検証機能により、LangGraphで状態スキーマを定義するのに特に適しています。
Pydanticは、データが指定された型や制約に適合しているかどうかを実行時に検証することができます。
"""
from pydantic import BaseModel, field_validator, ValidationError

class PydanticState(BaseModel):
    name: str
    mood: str # "happy" or "sad" 

    @field_validator('mood')
    @classmethod
    def validate_mood(cls, value):
        # Ensure the mood is either "happy" or "sad"
        if value not in ["happy", "sad"]:
            raise ValueError("Each mood must be either 'happy' or 'sad'")
        return value

try:
    state = PydanticState(name="John Doe", mood="mad")
except ValidationError as e:
    print("Validation Error:", e)

# PydanticStateをグラフでシームレスに使用できます。
# Build graph
builder = StateGraph(PydanticState)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)

# Logic
builder.add_edge(START, "node_1")
builder.add_conditional_edges("node_1", decide_mood)
builder.add_edge("node_2", END)
builder.add_edge("node_3", END)

# Add
graph = builder.compile()

# View
from utils import save_mermaid_to_html
save_mermaid_to_html(graph.get_graph().draw_mermaid(), "out/2_1_state_schema-3.html")

result = graph.invoke(PydanticState(name="Lance",mood="sad"))
print(result)
