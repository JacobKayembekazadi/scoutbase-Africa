"""
ScoutBase — Agent Orchestrator
Reads markdown agent definitions and generates intelligence reports using LLMs.
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional

AGENTS_DIR = Path(__file__).parent / "agents"

def load_agent(agent_name: str) -> str:
    """Load an agent's markdown definition."""
    path = AGENTS_DIR / f"{agent_name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Agent {agent_name} not found at {path}")
    return path.read_text()

def load_league_config(league: str = None) -> str:
    """Load league benchmarks."""
    path = AGENTS_DIR / "config" / "LEAGUES.md"
    if path.exists():
        content = path.read_text()
        if league:
            # Extract relevant section
            lines = content.split('\n')
            section = []
            in_section = False
            for line in lines:
                if league.lower() in line.lower() and line.startswith('#'):
                    in_section = True
                elif in_section and line.startswith('### '):
                    break
                if in_section:
                    section.append(line)
            if section:
                return '\n'.join(section)
        return content
    return ""

async def generate_scout_report(
    tracking_data: Dict,
    pose_data: Dict = None,
    league: str = None,
    model: str = "gemini"
) -> str:
    """Generate a full scout report using the Scout Agent."""
    agent_prompt = load_agent("SCOUT")
    league_context = load_league_config(league) if league else ""

    # Build the data payload
    data_summary = _summarize_tracking_data(tracking_data)
    if pose_data:
        data_summary += "\n\n## Pose Analysis Data\n" + json.dumps(pose_data, indent=2, default=str)

    prompt = f"""{agent_prompt}

## League Context
{league_context}

## Match Data
{data_summary}

Generate the scout report now. Follow the output format exactly."""

    return await _call_llm(prompt, model)

async def generate_match_report(
    tracking_data: Dict,
    pose_data: Dict = None,
    model: str = "gemini"
) -> str:
    """Generate a match performance report using the Analyst Agent."""
    agent_prompt = load_agent("ANALYST")
    data_summary = _summarize_tracking_data(tracking_data)

    if pose_data:
        data_summary += "\n\n## Pose Analysis\n" + json.dumps(pose_data, indent=2, default=str)

    prompt = f"""{agent_prompt}

## Match Data
{data_summary}

Generate the match performance report now."""

    return await _call_llm(prompt, model)

async def generate_medical_flags(
    pose_data: Dict,
    tracking_data: Dict = None,
    model: str = "gemini"
) -> str:
    """Generate medical risk flags using the Medical Agent."""
    agent_prompt = load_agent("MEDICAL")

    prompt = f"""{agent_prompt}

## Pose Analysis Data
{json.dumps(pose_data, indent=2, default=str)}

## Tracking Data Summary
{_summarize_tracking_data(tracking_data) if tracking_data else 'Not available'}

Assess injury risk for each player. Follow the output format exactly."""

    return await _call_llm(prompt, model)

async def generate_highlight_spec(
    tracking_data: Dict,
    model: str = "gemini"
) -> str:
    """Generate highlight reel specification using the Editor Agent."""
    agent_prompt = load_agent("EDITOR")
    data_summary = _summarize_tracking_data(tracking_data)

    prompt = f"""{agent_prompt}

## Match Tracking Data
{data_summary}

Generate the highlight reel specification."""

    return await _call_llm(prompt, model)

def _summarize_tracking_data(data: Dict) -> str:
    """Create a concise text summary of tracking data for LLM consumption."""
    if not data:
        return "No tracking data available."

    lines = []
    lines.append(f"**Match Duration**: {data.get('duration_seconds', 0):.0f}s ({data.get('duration_seconds', 0)/60:.1f} min)")
    lines.append(f"**Resolution**: {data.get('resolution', 'unknown')}")
    lines.append(f"**FPS**: {data.get('fps', 30)}")
    lines.append(f"**Players Tracked**: {data.get('players_tracked', 0)}")
    lines.append(f"**Total Frames**: {data.get('total_frames', 0)}")

    players = data.get("players", [])
    if isinstance(players, dict):
        players = list(players.values())

    lines.append(f"\n## Player Data ({len(players)} players)")

    for p in players[:20]:  # Limit to 20 players
        tid = p.get("track_id", "?")
        frames = p.get("frames_visible", 0)
        speed = p.get("avg_speed", 0)
        max_speed = p.get("max_speed", 0)
        sprints = p.get("sprint_count", 0)

        lines.append(f"\n### Track ID {tid}")
        lines.append(f"- Frames visible: {frames}")
        lines.append(f"- Avg speed: {speed:.1f} px/frame")
        lines.append(f"- Max speed: {max_speed:.1f} px/frame")
        lines.append(f"- Sprint count: {sprints}")

        # Add zone data if available
        zones = p.get("zone_distribution", {})
        if zones:
            lines.append(f"- Zone distribution: {json.dumps(zones)}")

    return '\n'.join(lines)

async def _call_llm(prompt: str, model: str = "gemini") -> str:
    """Call LLM with the given prompt."""
    if model == "gemini":
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
            model_obj = genai.GenerativeModel("gemini-2.5-pro-latest")
            response = model_obj.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating report with Gemini: {str(e)}"

    elif model == "claude":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model="claude-sonnet-4-6-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            return f"Error generating report with Claude: {str(e)}"

    return "Unknown model specified"
