
import pandas as pd
import plotly
import plotly.express as px
import plotly.io as pio
pio.templates.default = "plotly_white"
import plotly.graph_objects as go
import os
import pathlib
import json
import logging
import jax.numpy as jnp
from typing import List, Dict

from benchmarx.defaults import default_plotly_config
from benchmarx.metrics import Metrics, CustomMetric

from benchmarx.benchmark_result import BenchmarkResult


class Plotter:
    benchmark_result: BenchmarkResult

    def __init__(self, benchmark_result) -> None:
        self.benchmark_result = benchmark_result


    def plotly_figure(
        self, dataframe: pd.DataFrame, dropdown_options: List[Dict[str, str]]
    ) -> go.Figure:
        """ """
        markers = [
            "circle",
            "square",
            "diamond",
            "cross",
            "x",
            "triangle-up",
            "triangle-down",
            "triangle-left",
            "triangle-right",
            "triangle-ne",
            "triangle-se",
            "triangle-sw",
            "triangle-nw",
        ]
        colors_rgba = [
            'rgba(31, 119, 180,  1)',
            'rgba(255, 127, 14,  1)',
            'rgba(44, 160, 44,   1)',
            'rgba(214, 39, 40,   1)',
            'rgba(148, 103, 189, 1)',
            'rgba(140, 86, 75,   1)',
            'rgba(227, 119, 194, 1)',
            'rgba(127, 127, 127, 1)',
            'rgba(188, 189, 34,  1)',
            'rgba(23, 190, 207,  1)'
        ]
        colors_rgba_faint = [
            'rgba(31, 119, 180,  0.3)',
            'rgba(255, 127, 14,  0.3)',
            'rgba(44, 160, 44,   0.3)',
            'rgba(214, 39, 40,   0.3)',
            'rgba(148, 103, 189, 0.3)',
            'rgba(140, 86, 75,   0.3)',
            'rgba(227, 119, 194, 0.3)',
            'rgba(127, 127, 127, 0.3)',
            'rgba(188, 189, 34,  0.3)',
            'rgba(23, 190, 207,  0.3)'
        ]
        fig = go.Figure()

        # Add traces for each method and each dropdown option
        for i_method, method in enumerate(dataframe["Method"].unique()):
            method_df = dataframe[dataframe["Method"] == method]
            marker = dict(symbol=markers[i_method % len(markers)],
                          color=colors_rgba[i_method % len(colors_rgba)])
            fillcolor = colors_rgba_faint[i_method % len(colors_rgba_faint)]
            for option in dropdown_options:
                trace_mean = go.Scatter(
                    x=method_df["Iteration"],
                    y=method_df[option["value"] + "_mean"],
                    mode="lines+markers",
                    marker=marker,
                    hovertext=f"{method} - {option['label']}",
                    name=f"{method}",
                    visible=option["value"] == dropdown_options[0]["value"]
                )
                fig.add_trace(trace_mean)
                if not all([val == 0 for val in method_df[option["value"] + "_std"]]):
                    trace_plus_std = go.Scatter(
                        name='mean + std',
                        x=method_df['Iteration'],
                        y=method_df[option["value"] + "_mean"] + method_df[option["value"] + "_std"],
                        mode='lines',
                        line=dict(width=0),
                        showlegend=False,
                        hovertext=f"{method} - {option['label']}_upper",
                        visible=option["value"] == dropdown_options[0]["value"]
                    )
                    fig.add_trace(trace_plus_std)

                    trace_minus_std = go.Scatter(
                        name='mean - std',
                        x=method_df['Iteration'],
                        y=method_df[option["value"] + "_mean"] - method_df[option["value"] + "_std"],
                        line=dict(width=0),
                        mode='lines',
                        fillcolor=fillcolor,
                        fill='tonexty',
                        showlegend=False,
                        hovertext=f"{method} - {option['label']}_lower",
                        visible=option["value"] == dropdown_options[0]["value"]
                    )
                    fig.add_trace(trace_minus_std)
        # Update layout
        fig.update_layout(
            updatemenus=[
                {
                    "buttons": [
                        {
                            "method": "update",
                            "label": option["label"],
                            "args": [
                                {
                                    "visible": [
                                        option["value"] in trace.hovertext
                                        for trace in fig.data
                                    ]
                                }
                            ],
                            "args2": [
                                {"yaxis": {"title": option["label"], "type": "log"}}
                            ],
                        }
                        for option in dropdown_options
                    ],
                    "direction": "down",
                    "showactive": True,
                    "x": -0.14,
                    "xanchor": "left",
                    "y": 1.2,
                    "yanchor": "top",
                }
            ],
            xaxis={"title": "Iteration"},
            yaxis={"title": "", "type": "log"},
            title=str(dataframe.T[0]["Problem"]),  # Set your problem title here
        )

        fig.update_layout(
            dragmode="pan",
            title={
                "x": 0.5,
                "xanchor": "center",
            },
        )

        return fig

    def plot(
        self,
        metrics: List[str | CustomMetric],
        plotly_config=default_plotly_config,
        write_html: bool = False,
        path_to_write: str = "",
        include_plotlyjs: str = "cdn",
        full_html: bool = False
    ) -> None:
        """ 
        metrics, List[str | CustomMetric], string metrics are 
            from Metrics.metrics_to_plot: metrics to plot.
        plotly_config:          plotly config.
        write_html, bool:       if True, html file will be write according to path_to_write.
        include_plotlyjs:       string.
        full_html, bool:        full html.
        """
        dfs = self.benchmark_result.get_dataframes(df_metrics=metrics)
        for _, df in dfs.items():
            metrics_str = [metric for metric in metrics if isinstance(metric, str)]
            metrics_str += [
                metric.label
                for metric in metrics
                if isinstance(metric, CustomMetric)
            ]
            dropdown_options = [
                {"label": metric, "value": metric} for metric in metrics_str
            ]
            figure = self.plotly_figure(dataframe=df, dropdown_options=dropdown_options)
            figure.show(config=plotly_config)

            if write_html:
                figure.write_html(
                    path_to_write,
                    config=plotly_config,
                    include_plotlyjs="cdn",
                    full_html=False,
                )


def test_local():
    plotter = Plotter(
        # metrics= ['fs', 'xs_norm', 'f_gap', 'x_gap', 'grads_norm'],
        metrics=["fs", "xs_norm", "f_gap"],
        data_path="custom_method_data.json",
    )
    # plotter.plot()
    # data = plotter._sparse_data()
    # print(data.keys())


if __name__ == "__main__":
    test_local()
