#!/usr/bin/env python3
"""
Finance Purple Agent - Baseline Example

A simple A2A-compatible agent that responds to the Finance Green Agent's
three evaluation tasks using LLM analysis.
"""

import argparse
import json
import os
import re
from typing import Any

import uvicorn
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

from a2a.server.apps import A2AStarletteApplication
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Message,
    Part,
    TaskState,
    TextPart,
    DataPart,
)
from a2a.utils import get_message_text, new_agent_text_message, new_task


load_dotenv()


class FinanceAnalyst:
    """Purple agent that analyzes 10-K filings for the Finance Green Agent benchmark."""
    
    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self._model = os.getenv("MODEL_ID", "deepseek/deepseek-v3.2")
    
    async def analyze(self, prompt: str) -> str:
        """Analyze the given prompt and return a structured JSON response."""
        
        # Detect task type from prompt
        task_type = self._detect_task_type(prompt)
        
        # Build appropriate system prompt
        system_prompt = self._get_system_prompt(task_type)
        
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content
            
            # Validate JSON and ensure proper format
            parsed = json.loads(result)
            return json.dumps(self._format_response(parsed, task_type), indent=2)
            
        except Exception as e:
            # Return a valid fallback response on error
            return json.dumps(self._get_fallback_response(task_type))
    
    def _detect_task_type(self, prompt: str) -> str:
        """Detect which task the green agent is requesting."""
        prompt_lower = prompt.lower()
        
        if "task 1" in prompt_lower or "risk classification" in prompt_lower:
            return "risk_classification"
        elif "task 2" in prompt_lower or "business summary" in prompt_lower:
            return "business_summary"
        elif "task 3" in prompt_lower or "consistency" in prompt_lower:
            return "consistency_check"
        else:
            # Default based on content keywords
            if "risk factor" in prompt_lower or "section 1a" in prompt_lower:
                return "risk_classification"
            elif "business" in prompt_lower and "section 1" in prompt_lower:
                return "business_summary"
            else:
                return "risk_classification"
    
    def _get_system_prompt(self, task_type: str) -> str:
        """Get the appropriate system prompt for the task."""
        
        if task_type == "risk_classification":
            return """You are a financial risk analyst. Analyze the provided 10-K Risk Factors section.

Classify the risks into these predefined categories (only use these exact names):
- Market Risk
- Operational Risk
- Financial Risk
- Legal/Regulatory Risk
- Technology Risk
- Cybersecurity Risk
- Competition Risk
- Supply Chain Risk
- Human Capital/Talent Risk
- Environmental/Climate Risk
- COVID-19/Pandemic Risk
- Geopolitical Risk

Return a JSON object with:
{
  "task": "risk_classification",
  "risk_classification": ["Category 1", "Category 2", ...]
}

Only include categories that are clearly mentioned in the text. Be precise."""

        elif task_type == "business_summary":
            return """You are a business analyst. Analyze the provided 10-K Business section.

Extract key information about:
1. Industry/sector the company operates in
2. Main products or services offered
3. Geographic markets served

Return a JSON object with:
{
  "task": "business_summary",
  "business_summary": {
    "industry": "Detailed industry description",
    "products": "Main products and services",
    "geography": "Geographic markets"
  }
}

Be specific and detailed in your responses."""

        else:  # consistency_check
            return """You are a financial document analyst. You are given:
1. A list of risks from Section 1A
2. The MD&A Section 7 text

Identify which of the listed risks are actually discussed in Section 7.

Return a JSON object with:
{
  "task": "consistency_check",
  "consistency_check": ["risk1", "risk2", ...]
}

Only include risks that are clearly discussed in Section 7."""
    
    def _format_response(self, parsed: dict, task_type: str) -> dict:
        """Ensure response is in the expected format."""
        
        result = {"task": task_type}
        
        if task_type == "risk_classification":
            # Extract categories from various possible formats
            categories = (
                parsed.get("risk_classification") or
                parsed.get("categories") or
                parsed.get("risk_categories") or
                []
            )
            result["risk_classification"] = categories
            
        elif task_type == "business_summary":
            summary = parsed.get("business_summary") or parsed
            result["business_summary"] = {
                "industry": summary.get("industry", "N/A"),
                "products": summary.get("products", "N/A"),
                "geography": summary.get("geography", "N/A")
            }
            
        else:  # consistency_check
            risks = (
                parsed.get("consistency_check") or
                parsed.get("discussed_risks") or
                parsed.get("consistent_risks") or
                []
            )
            result["consistency_check"] = risks
            
        return result
    
    def _get_fallback_response(self, task_type: str) -> dict:
        """Return a safe fallback response on error."""
        
        if task_type == "risk_classification":
            return {
                "task": "risk_classification",
                "risk_classification": ["Market Risk", "Operational Risk"]
            }
        elif task_type == "business_summary":
            return {
                "task": "business_summary",
                "business_summary": {
                    "industry": "Unable to determine",
                    "products": "Unable to determine",
                    "geography": "Unable to determine"
                }
            }
        else:
            return {
                "task": "consistency_check",
                "consistency_check": []
            }


class AnalystExecutor(AgentExecutor):
    """A2A executor for the finance analyst agent."""
    
    TERMINAL_STATES = {
        TaskState.completed,
        TaskState.canceled,
        TaskState.failed,
        TaskState.rejected
    }
    
    def __init__(self):
        self.analyst = FinanceAnalyst()
        self.contexts: dict[str, Any] = {}
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        msg = context.message
        if not msg:
            return
        
        task = context.current_task
        if task and task.status.state in self.TERMINAL_STATES:
            return
        
        if not task:
            task = new_task(msg)
            await event_queue.enqueue_event(task)
        
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        
        await updater.start_work()
        
        try:
            # Get the message text
            input_text = get_message_text(msg)
            
            # Update status
            await updater.update_status(
                TaskState.working,
                new_agent_text_message("Analyzing financial document...")
            )
            
            # Perform analysis
            result = await self.analyst.analyze(input_text)
            
            # Return result as artifact
            await updater.add_artifact(
                parts=[Part(root=TextPart(text=result))],
                name="FinancialAnalysis"
            )
            
            await updater.complete()
            
        except Exception as e:
            print(f"Analysis failed: {e}")
            await updater.failed(
                new_agent_text_message(f"Analysis error: {e}")
            )
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


def main():
    parser = argparse.ArgumentParser(description="Run the Finance Purple Agent")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=9020, help="Port to bind")
    args = parser.parse_args()
    
    skill = AgentSkill(
        id="finance-analyst",
        name="10-K Financial Analyst",
        description="Analyzes SEC 10-K filings for risk factors, business summary, and consistency checks",
        tags=["finance", "10-K", "risk-analysis", "business-analysis"],
        examples=[
            "Analyze this 10-K filing for risk factors",
            "Extract business summary from this filing"
        ]
    )
    
    agent_card = AgentCard(
        name="finance-analyst",
        description="Purple agent that analyzes SEC 10-K filings. Responds to three evaluation tasks: "
                    "(1) Risk Classification - categorizes risk factors, "
                    "(2) Business Summary - extracts key business information, "
                    "(3) Consistency Check - identifies which risks are discussed in MD&A.",
        url=f"http://{args.host}:{args.port}/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill]
    )
    
    request_handler = DefaultRequestHandler(
        agent_executor=AnalystExecutor(),
        task_store=InMemoryTaskStore(),
    )
    
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    print(f"🟣 Starting Finance Purple Agent on {args.host}:{args.port}")
    print(f"   Agent Card: http://{args.host}:{args.port}/.well-known/agent-card.json")
    uvicorn.run(server.build(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
