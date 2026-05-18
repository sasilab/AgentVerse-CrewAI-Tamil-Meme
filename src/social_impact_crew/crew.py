"""CrewAI crew wiring: agents + tasks + sequential process.

The @CrewBase decorator binds the YAML configs to this class so the @agent
and @task methods can reference entries by name (self.agents_config[...]).
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from .llm import build_llm
from .tools.custom_tool import GeocodeTool, PollutionTool, WeatherTool


@CrewBase
class SocialImpactCrew:
    """Weather + Pollution + Tamil Meme Writer crew."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ----- Agents -----

    @agent
    def weather_reporter(self) -> Agent:
        return Agent(
            config=self.agents_config["weather_reporter"],
            tools=[GeocodeTool(), WeatherTool()],
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
        # Higher temperature so the meme has more bite than the data agents.
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
