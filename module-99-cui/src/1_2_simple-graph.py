"""
State

まず、グラフの状態を定義します。
状態スキーマは、グラフ内のすべてのノードとエッジの入力スキーマとして機能します。
Pythonのtypingモジュールから TypedDict クラスをスキーマとして使用しましょう。これにより、キーに対する型ヒントが提供されます。
"""
from typing_extensions import TypedDict

class State(TypedDict):
    graph_state: str

"""
Nodes

ノードは単なるPython関数です。
最初の位置引数は、上で定義された状態です。
状態は上で定義されたスキーマを持つTypedDictであるため、各ノードはstate['graph_state']を使用してキーgraph_stateにアクセスできます。
各ノードは、状態キーgraph_stateの新しい値を返します。
デフォルトでは、各ノードが返す新しい値は、以前の状態値を上書きします。
"""
def node_1(state):
    print("---Node 1---")
    return {"graph_state": state['graph_state'] +" I am"}

def node_2(state):
    print("---Node 2---")
    return {"graph_state": state['graph_state'] +" happy!"}

def node_3(state):
    print("---Node 3---")
    return {"graph_state": state['graph_state'] +" sad!"}

"""
Edges

エッジはノードを接続します。
通常のエッジは、例えば、常にnode_1からnode_2に進みたい場合に使用されます。
条件付きエッジは、ノード間を選択的にルーティングしたい場合に使用されます。
条件付きエッジは、何らかのロジックに基づいて次に訪れるノードを返す関数として実装されます。
"""
import random
from typing import Literal

def decide_mood(state) -> Literal["node_2", "node_3"]:
    
    # Often, we will use state to decide on the next node to visit
    user_input = state['graph_state'] 
    
    # Here, let's just do a 50 / 50 split between nodes 2, 3
    if random.random() < 0.5:

        # 50% of the time, we return Node 2
        return "node_2"
    
    # 50% of the time, we return Node 3
    return "node_3"

"""
Graph Construction

ここで、上で定義したコンポーネントからグラフを構築します。
StateGraphクラスは、使用できるグラフクラスです。
まず、上で定義したStateクラスでStateGraphを初期化します。
次に、ノードとエッジを追加します。
STARTノード（ユーザー入力をグラフに送る特別なノード）を使用して、グラフの開始点を示します。
ENDノードは、終端ノードを表す特別なノードです。
最後に、グラフをコンパイルして、グラフ構造に対していくつかの基本的なチェックを行います。
グラフをMermaidダイアグラムとして視覚化することができます。
"""
from IPython.display import Image, display
from langgraph.graph import StateGraph, START, END

# Build graph
builder = StateGraph(State)
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
# display(Image(graph.get_graph().draw_mermaid_png()))

"""
Graph Invocation

コンパイルされたグラフは実行可能プロトコルを実装しています。
これにより、LangChainコンポーネントを実行するための標準的な方法が提供されます。
invokeはこのインターフェースの標準的なメソッドの1つです。
入力は辞書 {"graph_state": "こんにちは、ランスです。"} で、これがグラフ状態辞書の初期値を設定します。
invokeが呼び出されると、グラフはSTARTノードから実行を開始します。
定義されたノード（node_1、node_2、node_3）を順番に進んでいきます。
条件付きエッジは、50/50の決定ルールを使用してnode 1からnode 2または3に進みます。
各ノード関数は現在の状態を受け取り、新しい値を返します。これがグラフ状態を上書きします。
実行はENDノードに到達するまで続きます。
"""
result = graph.invoke({"graph_state" : "Hi, this is Lance."})
print(result)
