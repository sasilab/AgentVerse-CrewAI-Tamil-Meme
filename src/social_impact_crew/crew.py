"""CrewAI crew wiring: agents + tasks + sequential process.

The @CrewBase decorator binds the YAML configs to this class so the @agent
and @task methods can reference entries by name (self.agents_config[...]).
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from .llm import build_llm
from .tools.custom_tool import PollutionTool, WeatherTool


@CrewBase
class SocialImpactCrew:
    """Weather + Pollution + Tamil Meme Writer crew."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ----- Agents -----

    @agent
    def weather_reporter(self) -> Agent:
        # Geocoding is done in api.py / main.py BEFORE kickoff and passed in
        # as {lat}/{lon} inputs, so the agent only needs WeatherTool. This
        # removes the LLM's ability to hallucinate coordinates for the weather
        # call (which was the root cause of wrong-city bugs).
        return Agent(
            config=self.agents_config["weather_reporter"],
            tools=[WeatherTool()],
            llm=build_llm(),
            verbose=True,
        )

    @agent
    def pollution_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["pollution_analyst"],
            tools=[PollutionTool()],
            llm=build_llm(),
            verbose=True,
        )

    @agent
    def tamil_meme_writer(self) -> Agent:
        # No tools — pure creative writing on top of context.
        # Higher temperature so creative personalities have more variety.
        # Note: misleading legacy name — this agent now adapts to the chosen
        # personality (sarcastic_meme / caring_friend / serious_analyst / ...).
        return Agent(
            config=self.agents_config["tamil_meme_writer"],
            llm=build_llm(temperature=0.9),
            verbose=True,
        )

    # ----- Tasks -----

    @task
    def weather_task(self) -> Task:
        return Task(config=self.tasks_config["weather_task"])

    @task
    def pollution_task(self) -> Task:
        return Task(config=self.tasks_config["pollution_task"])

    @task
    def meme_task(self) -> Task:
        return Task(config=self.tasks_config["meme_task"])

    # ----- Crew -----

    @crew
    def crew(self) -> Crew:
        # Sequential: weather -> pollution -> meme. Each step's output flows
        # into the next via the 'context' declared in tasks.yaml.
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
