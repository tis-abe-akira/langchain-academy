"""
ファイナンス計算をツールとして持つエージェントを作成します。
agent.pyをもとにしています。
"""
from calendar import month
from dotenv import load_dotenv
load_dotenv()

##
# Goals
#
# さて、これを汎用エージェントアーキテクチャに拡張できます。
# 上記のルーターでは、モデルを呼び出し、ツールを呼び出すことを選択した場合、ユーザーにToolMessageを返しました。
# しかし、そのToolMessageを単にモデルに渡したらどうなるでしょうか？
# モデルに(1)別のツールを呼び出すか(2)直接応答するかを任せることができます。
# これがReActの直感であり、汎用エージェントアーキテクチャです。
# - act - モデルに特定のツールを呼び出させる
# - observe - ツールの出力をモデルに渡す
# - reason - モデルにツールの出力を基に次に何をするか（例: 別のツールを呼び出すか、直接応答するか）を判断させる
# この汎用アーキテクチャは、多くの種類のツールに適用できます。
##

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

@tool
def amortization_calculation(principal: int, annual_interest_rate: float, num_payments: int) -> int:
    """Amortization calculation tool.
    Args:
        principal (int): Principal amount.
        annual_interest_rate (float): Annual interest rate.
        num_payments (int): Number of payments.
    Returns:
        int: Monthly payment.
    """
    # 月利率の計算
    monthly_interest_rate = annual_interest_rate / 1200
    # 毎月の返済額を計算する式
    monthly_payment = principal * (monthly_interest_rate * (1 + monthly_interest_rate) ** num_payments) / ((1 + monthly_interest_rate) ** num_payments - 1)
    # 計算結果を切り捨てて整数に変換
    return int(monthly_payment)

@tool
def net_present_value_calculation(cash_flow: int, discount_rate: float, start_month: int, end_month: int) -> int:
    """Net present value calculation tool.
    Args:
        cash_flow (int): Cash flow.
        discount_rate (float): Discount rate.
        start_month (int): Start month.
        end_month (int): End month.
    Returns:
        int: Net present value.
    """
    npv = 0
    monthly_rate = discount_rate / 1200
    for t in range(start_month, end_month + 1):
        npv += cash_flow / (1 + monthly_rate) ** t
    return int(npv)

tools = [amortization_calculation, net_present_value_calculation]
llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools(tools)


# LLMを作成し、全体的に望ましいエージェントの動作をプロンプトしましょう。
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage

# System message
sys_msg = SystemMessage(content="You are a helpful assistant tasked with performing financial task on a set of inputs.")

# Node
def assistant(state: MessagesState):
   return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

# 以前と同様に、MessagesStateを使用し、ツールのリストを持つToolsノードを定義します。
# Assistantノードは、ツールがバインドされたモデルです。
# AssistantノードとToolsノードでグラフを作成します。
# tools_conditionエッジを追加し、Assistantがツールを呼び出すかどうかに基づいてEndまたはToolsにルーティングします。
# ここで、新しいステップを1つ追加します:
# ToolsノードをAssistantに戻してループを形成します。
# - Assistantノードが実行された後、tools_conditionがモデルの出力がツール呼び出しかどうかを確認します。
# - もしツール呼び出しであれば、フローはToolsノードに向かいます。
# - ToolsノードはAssistantに戻ります。
# - モデルがツールを呼び出す限り、このループは続きます。
# - モデルの応答がツール呼び出しでない場合、フローはENDに向かい、プロセスが終了します。

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
save_mermaid_to_html(react_graph.get_graph().draw_mermaid(), "out/agent_2.html")


# Agent実行
### No tool call
# messages = [HumanMessage(content="空が青く見えるのは何故ですか？")]

### Amortization Calculation
# messages = [HumanMessage(content="元本300万円、年利率2.4%、返済回数96回の場合の月々の返済額を計算してください。")]

### Net Present Value Calculation
content = """割引率年利が1.8%とした場合、
プロジェクトの効果が6ヶ月後から36ヶ月間に渡り月々500,000円出るとします。このプロジェクトの現在価値はいくらですか？
"""
messages = [HumanMessage(content=content)]

messages = react_graph.invoke({"messages": messages})

for m in messages['messages']:
    m.pretty_print()
