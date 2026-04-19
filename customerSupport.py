from langgraph.graph import StateGraph, START, END, add_messages
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from pydantic import Field,BaseModel
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage,AIMessage,ToolMessage
import json
import re
load_dotenv()

llm=init_chat_model("gemini-2.5-flash", model_provider="google_genai")


class CustomerSupportGraph(TypedDict):
    ticket_id: str
    status: str
    short_summary: str
    issue_type:str
    order_id: str
    customer_email: str
    missing_info: str
    sentiment: str
    product_id: str
    reason: str
    body: str
    subject: str
    tier: int
    expected_action: str
    intent: str
    urgency: str
    messages: Annotated[list[BaseMessage], add_messages]

class CustomerSupportState(BaseModel):
    issue_type: str = Field(..., description="Type of issue (refund / order_status / product_issue / cancel / policy / complaint)")
    intent: str = Field(..., description="What the user wants")
    urgency: str = Field(..., description="Urgency level (low / medium / high)")
    sentiment: str = Field(..., description="Sentiment of the message (positive / neutral / negative)")
    short_summary: str = Field(..., description="A one-line summary of the issue")
    missing_info: str = Field(..., description="Any missing information needed to resolve the issue (like order_id, email, etc.)")  



with open("./documents/customers.json","r") as f:
    customer_data=json.load(f)

with open("./documents/orders.json","r") as f:
    order_data=json.load(f)

with open("./documents/products.json","r") as f:
    product_data=json.load(f)

with open("./documents/knowledge-base.md","r") as f:
    knowledge_base=f.read()

    
def progress_node(state: CustomerSupportGraph) -> CustomerSupportGraph:
    print("Progressing node executing")

    prompt = f"""
    You are an AI assistant that extracts structured information from customer tickets.

    Extract the following fields:
    - issue_type (refund / order_status / product_issue / cancel / policy / complaint)
    - intent (what user wants)
    - urgency (low / medium / high)
    - sentiment (positive / neutral / negative)
    - short_summary (1 line)
    - missing_info (what is missing like order_id, email)

    Rules:
    - Return ONLY JSON
    - Do NOT explain anything

    Ticket:
    Subject: {state.get("subject", "")}
    Message: {state.get("body", "")}
    Expected Action: {state.get("expected_action", "")}
    """

    response = llm.with_structured_output(CustomerSupportState).invoke(prompt)
    print(f"Response: {response}")

    return {
        "issue_type": response.issue_type,
        "intent": response.intent,
        "urgency": response.urgency,
        "sentiment": response.sentiment,
        "short_summary": response.short_summary,
        "missing_info": response.missing_info
        
    }
    
@tool
def get_order(order_id: str) -> dict:
    '''Use this tool when you need order details like status, date,items etc.'''
    print(f"Fetching details for order ID: {order_id}")

    for order in order_data:
        if order["order_id"] == order_id:
            return order
    return {"error": "Order not found"}


@tool
def get_customer(customer_email: str) -> dict:
    '''Use this tool when customer identity or tier is needed.Helpful for handling exceptions like VIP customers.'''
    print(f"Fetching details for customer email: {customer_email}")

    for customer in customer_data:
        if customer["email"] == customer_email:
            return customer
    return {"error": "Customer not found"}



@tool
def get_product(product_id: str) -> dict:
    '''Use this tool when product-related issues arise like defects or warranty claims.'''
    print(f"Fetching details for product ID: {product_id}")

    for product in product_data:
        if product["product_id"] == product_id:
            return product
    return {"error": "Product not found"}



@tool
def search_knwledge_base(query: str) -> list:
    '''Use this tool for general questions like return policy, exchange rules, etc.'''
    print(f"Searching knowledge base for query: {query}")

    """Search relevant info from knowledge base"""
    query = query.lower()

    lines = query.split("\n")
    results = [line for line in lines if query in line.lower()]

    if results:
        return "\n".join(results[:5])  # top 5 matches
    return "No relevant information found"

@tool
def check_refund_eligibility(order_id: str) -> dict:
    """Check if order is eligible for refund"""
    print(f"Checking refund eligibility for order ID: {order_id}")

    for order in order_data:
        if order["order_id"] == order_id:
            # example rules
            if order.get("status") != "delivered":
                return {"eligible": False, "reason": "Order not delivered yet"}

            if order.get("refund_status"):
                return {"eligible": False, "reason": "Already refunded"}

            # simple return window logic (hackathon level)
            return {
                "eligible": True,
                "reason": "Within return window",
                "amount": order.get("amount", 0)
            }

    return {"eligible": False, "reason": "Order not found"}


@tool
def issue_refund(order_id: str, amount: float) -> dict:
    """Process refund"""

    for order in order_data:
        if order["order_id"] == order_id:

            if order.get("refund_status"):
                return {"status": "failed", "reason": "Already refunded"}

            # update state (simulate DB update)
            order["refund_status"] = "completed"

            return {
                "status": "success",
                "order_id": order_id,
                "amount_refunded": amount
            }

    return {"status": "failed", "reason": "Order not found"}
    

@tool
def send_reply(ticket_id: str, message: str) -> dict:
    """Send reply to customer"""

    print(f"[REPLY SENT] Ticket: {ticket_id}")
    print(f"Message: {message}")

    return {
        "ticket_id": ticket_id,
        "status": "sent",
        "message": message
    }

@tool
def escalate(ticket_id: str, summary: str, priority: str) -> dict:
    """Escalate issue to human"""

    print(f"[ESCALATED] Ticket: {ticket_id}")
    print(f"Priority: {priority}")
    print(f"Summary: {summary}")

    return {
        "ticket_id": ticket_id,
        "status": "escalated",
        "priority": priority,
        "summary": summary
    }


# Make tool list
tools = [get_customer, get_product, search_knwledge_base, check_refund_eligibility, issue_refund, send_reply, escalate, get_order]


# Make the LLM tool-aware
llm_with_tools = llm.bind_tools(tools) # here tell about the tools to the LLM

def customer_support_node(state: CustomerSupportGraph) -> CustomerSupportGraph:
    print("Customer support node executing..")

    prompt = f"""
You are an autonomous customer support AI agent.

GOAL:
You MUST fully resolve the ticket by calling tools step-by-step.

AVAILABLE TOOLS:
- get_order(order_id)
- check_refund_eligibility(order_id)
- issue_refund(order_id, amount)
- get_customer(email)
- get_product(product_id)
- search_knowledge_base(query)
- send_reply(ticket_id, message)
- escalate(ticket_id, summary, priority)

CRITICAL RULES:
- You MUST call at least one tool
- You MUST continue until final action is reached
- FINAL ACTION MUST BE:
    → send_reply (if resolved)
    → escalate (if unsure / missing info / error)

FLOW RULES:
1. If order_id exists → ALWAYS call get_order FIRST
2. Then decide next step:
   - refund → check_refund_eligibility → issue_refund
   - product issue → get_product
   - customer issue → get_customer
   - policy → search_knowledge_base
3. NEVER stop before calling send_reply or escalate
4. DO NOT repeat same tool
5. If missing info → escalate OR ask via send_reply

IMPORTANT:
- You are NOT allowed to stop early
- Every ticket MUST end with send_reply OR escalate

Ticket Info:
Issue Type: {state.get("issue_type")}
Intent: {state.get("intent")}
Order ID: {state.get("order_id")}
Customer Email: {state.get("customer_email")}
Summary: {state.get("short_summary")}
Missing Info: {state.get("missing_info")}
"""

    messages = state.get("messages", [])

    if not messages:
        messages.append(SystemMessage(content=prompt))
        messages.append(HumanMessage(content=state.get("body", "")))

    response = llm_with_tools.invoke(messages)
    messages.append(response)

    
    return {"messages": messages}

def regex_extract_node(state: CustomerSupportGraph) -> CustomerSupportGraph:
    print("Extracting information using regex..")
    text = f"""
    {state.get("subject", "")}
    {state.get("body", "")}
    {state.get("customer_email", "")}
    """
    # ticket_id (already present)
    ticket_id = state.get("ticket_id")

    # order_id
    order_match = re.search(r'ORD-\d+', text)
    order_id = order_match.group(0) if order_match else None

    # email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    customer_email = email_match.group(0) if email_match else state.get("customer_email")

    # product_id
    product_match = re.search(r'P\d+', text)
    product_id = product_match.group(0) if product_match else None

    return {
        "ticket_id": ticket_id,
        "order_id": order_id,
        "customer_email": customer_email,
        "product_id": product_id
    }


tool_node = ToolNode(tools)

graph = StateGraph(CustomerSupportGraph)
graph.add_node("regex_extract_node", regex_extract_node)
graph.add_node("customer_support_node", customer_support_node)
graph.add_node("progress_node", progress_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "regex_extract_node")
graph.add_edge("regex_extract_node", "progress_node")
graph.add_edge("progress_node", "customer_support_node")
graph.add_conditional_edges("customer_support_node", tools_condition)
graph.add_edge("tools", "customer_support_node")


workflow = graph.compile()
initial_state =     {
    "ticket_id": "TKT-005",
    "customer_email": "emma.collins@email.com",
    "subject": "Return request",
    "body": "Hi team, I'd like to return the two bluetooth speakers I ordered back in December (ORD-1005). I know it might be past the return window but I've been traveling. Can you help?",
    "source": "ticket_queue",
    "created_at": "2024-03-15T08:45:00Z",
    "tier": 2,
    "expected_action": "return window expired — but VIP customer with pre-approved exception, approve return after checking customer notes"
  }


#Case for Handly single ticket
def build_final_output(state):

    actions = []
    final_reply = ""
    status = "pending"

    messages = state.get("messages", [])

    for msg in messages:

        # 1. Collect tool calls (AIMessage)
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for call in msg.tool_calls:
                tool_name = call.get("name")
                if tool_name:
                    actions.append(tool_name)

        # 2. Extract tool results (ToolMessage)
        if isinstance(msg, ToolMessage):
            tool_name = msg.name

            try:
                data = json.loads(msg.content)
            except:
                data = {}

            #  Reply extract
            if tool_name == "send_reply":
                final_reply = data.get("message", "")
                status = "resolved"

            # Escalation case
            elif tool_name == "escalate":
                final_reply = f"Escalated: {data.get('summary', '')}"
                status = "escalated"

    # fallback
    if not final_reply:
        final_reply = "Request processed."

    # structured result
    result = {
        "ticket_id": state.get("ticket_id"),
        "actions": actions,
        "status": status
    }

    return result, final_reply, actions


all_results = []

graph_output = workflow.invoke(initial_state)
result, reply, actions = build_final_output(graph_output)

all_results.append({
    "ticket_id": result["ticket_id"],
    "actions": actions,
    "status": result["status"],
    "reply": reply
})



with open("audit_log.json", "a+") as f:
    json.dump(all_results, f, indent=4)




# code for handling multiple tickets work correctly but exceed the limit of Google Gemini API
# with open("./documents/tickets.json","r") as f:
#     tickets_data=json.load(f)

# all_results = []

# for ticket in tickets_data:
#     print(ticket["ticket_id"])
#     try:
#         graph_output = workflow.invoke(ticket)
#     except:
#         time.sleep(3)
#         graph_output = workflow.invoke(ticket)
#     result, reply, actions = build_final_output(graph_output)

#     all_results.append({
#         "ticket_id": result["ticket_id"],
#         "actions": actions,
#         "status": result["status"],
#         "reply": reply
#     })




# with open("audit_log.json", "w") as f:
#     json.dump(all_results, f, indent=4)


