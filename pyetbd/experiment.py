from pyetbd.organisms import Organism
from pyetbd.schedules import Schedule
from pyetbd.settings_classes import ExperimentSettings
from pyetbd.algorithm import Algorithm
from pyetbd.utils import progress_logger, timer
import pandas as pd


class Experiment:
    def __init__(
        self,
        settings: ExperimentSettings,
        schedule_arrangements: list[list[Schedule]],
        log_progress: bool,
    ):
        self.settings = settings
        self.schedule_arrangements = schedule_arrangements
        self.log_progress = log_progress
        self._create_organism()
        self._create_output_dict()
        self._create_algorithm()
        self._create_progress_logger()

    def _create_organism(self):
        self.organism = Organism()

    def _create_algorithm(self):
        self.algorithm = Algorithm(self.organism)

    def _create_progress_logger(self):
        self.progress_logger = progress_logger.ProgressLogger(self.settings.file_stub)
        self.progress_logger.create_progress_bars(
            self.settings.reps, len(self.schedule_arrangements), self.settings.gens
        )

    def _create_output_dict(self):
        self.data_output = {
            "Rep": [],
            "Sch": [],
            "Gen": [],
            "Emissions": [],
        }
        for i in range(len(self.schedule_arrangements[0])):
            self.data_output[f"B{i}"] = []
            self.data_output[f"R{i}"] = []
            self.data_output[f"P{i}"] = []

    def _save_data(self):
        df = pd.DataFrame(self.data_output)
        df.to_csv(f"{self.settings.file_stub}.csv")

    @timer.timer
    def run(self):
        for rep in range(self.settings.reps):
            for arrangement in self.schedule_arrangements:
                if self.settings.reinitialize_population:
                    self.organism.init_population()

                for gen in range(self.settings.gens):
                    self.organism.emit()
                    self.data_output["Rep"].append(rep)
                    self.data_output["Sch"].append(
                        self.schedule_arrangements.index(arrangement)
                    )
                    self.data_output["Gen"].append(gen)
                    self.data_output["Emissions"].append(self.organism.emitted)

                    reinforcement_available = False
                    schedule_to_deliver_reinforcement = (
                        self.settings
                    )  # default to the experiment settings
                    punishment_available = False
                    schedule_to_deliver_punishment = self.settings

                    for schedule in arrangement:
                        # update whether the emitted response is in the response class
                        if schedule.in_response_class(self.organism.emitted):
                            self.data_output[f"B{arrangement.index(schedule)}"].append(
                                1
                            )

                        else:
                            self.data_output[f"B{arrangement.index(schedule)}"].append(
                                0
                            )

                        # run the schedule and update the data_output if the schedule is a reinforcement schedule
                        if schedule.settings.is_reinforcement_schedule:
                            self.data_output[f"P{arrangement.index(schedule)}"].append(
                                0
                            )
                            reinforced = schedule.run(self.organism.emitted)

                            if reinforced:
                                schedule_to_deliver_reinforcement = schedule.settings
                                reinforcement_available = True
                                self.data_output[
                                    f"R{arrangement.index(schedule)}"
                                ].append(1)

                            else:
                                self.data_output[
                                    f"R{arrangement.index(schedule)}"
                                ].append(0)

                        # run the schedule and update the data_output if the schedule is a punishment schedule
                        else:
                            self.data_output[f"R{arrangement.index(schedule)}"].append(
                                0
                            )
                            punished = schedule.run(self.organism.emitted)

                            if punished:
                                schedule_to_deliver_punishment = schedule.settings
                                punishment_available = True
                                self.data_output[
                                    f"P{arrangement.index(schedule)}"
                                ].append(1)

                            else:
                                self.data_output[
                                    f"P{arrangement.index(schedule)}"
                                ].append(0)

                    # run the algorithm on the organism
                    self.algorithm.run(
                        reinforcement_available,
                        punishment_available,
                        schedule_to_deliver_reinforcement,
                        schedule_to_deliver_punishment,
                    )

                    # update the progress of the experiment
                    if gen % 1000 == 0 and self.log_progress:
                        self.progress_logger.log_progress(
                            rep, self.schedule_arrangements.index(arrangement), gen
                        )

        if self.log_progress:
            self.progress_logger.log_progress(
                self.settings.reps,
                len(self.schedule_arrangements),
                self.settings.gens,
                end="\n",
            )

        self._save_data()
