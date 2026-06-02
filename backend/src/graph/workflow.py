from langgraph.graph import StateGraph, END

from backend.src.graph.state import VideoAuditState

from backend.src.graph.nodes import (
    index_video_node,
    compliance_audit_node as audit_content_node
)

# This module defines the  DAG that orchestrates the video compliance audit process using langgraph. It constructs a directed graph where each node represents a specific processing step in the video audit processt. 
# The graph is compiled into an executable app that can be run with the appropriate input state. It connects the nodes using the StateGraph from LaangGraph
# START -> index_video_nod -> audit_content_node -> END

def create_graph() -> StateGraph:
    """
    Constructs and compiles the workflow graph for video compliance auditing, The graph consists of two main nodes: index_video_node and audit_content_node.

    1. 'index_video_node': Responsible for downloading and indexing the video.
    2. 'audit_content_node': Responsible for auditing the content for the compliance issues.

    The graph is designed to be linear, where the output of the indexing node feeds directly into the auditing node. The final output of the graph is the result of the compliance audit.

    Returns:
        StateGraph: The compiled workflow graph ready for execution.
    """
    # Initialize the graph with the state schema
    workflow = StateGraph(VideoAuditState)

    # Add nodes to the graph
    workflow.add_node("indexer", index_video_node)
    workflow.add_node("auditor", audit_content_node)

    # Define the entry point
    workflow.set_entry_point("indexer")

    # Add edges to the graph
    workflow.add_edge("indexer", "auditor")

    # Once the audit is complete, the workflow ends and the final report is generated.
    workflow.add_edge("auditor", END)

    # Compile the graph into an executable app
    app = workflow.compile()
    return app

# Create the workflow app
app = create_graph()
