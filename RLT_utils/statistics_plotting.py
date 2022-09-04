import plotly_express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from statsmodels.tsa.stattools import pacf, acf
from statsmodels.graphics.gofplots import qqplot

def create_corr_plot(series, nlags=40, plot_pacf=False):
    '''The autocorrelation function (ACF) assesses the correlation between observations in a time series for a set 
    of lags.  The ACF for time series y is given by: Corr (yt,yt−k), k=1,2,….
    
    The partial autocorrelation at lag k is the correlation that results after removing the effect of any correlations 
    due to the terms at shorter lags.
    '''

    corr_array = pacf(series.dropna(), nlags, alpha=0.05) if plot_pacf else acf(series.dropna(), nlags, alpha=0.05)
    lower_y = corr_array[1][:,0] - corr_array[0]
    upper_y = corr_array[1][:,1] - corr_array[0]

    fig = go.Figure()
    [fig.add_scatter(x=(x,x), y=(0,corr_array[0][x]), mode='lines',line_color='#3f3f3f') 
     for x in range(len(corr_array[0]))]
    fig.add_scatter(x=np.arange(len(corr_array[0])), y=corr_array[0], mode='markers', marker_color='#1f77b4',
                   marker_size=12)
    fig.add_scatter(x=np.arange(len(corr_array[0])), y=upper_y, mode='lines', line_color='rgba(255,255,255,0)')
    fig.add_scatter(x=np.arange(len(corr_array[0])), y=lower_y, mode='lines',fillcolor='rgba(32, 146, 230,0.3)',
            fill='tonexty', line_color='rgba(255,255,255,0)')
    fig.update_traces(showlegend=False)
    fig.update_xaxes(range=[-1,42])
    fig.update_yaxes(zerolinecolor='#000000')
    
    title='Partial Autocorrelation (PACF)' if plot_pacf else 'Autocorrelation (ACF)'
    fig.update_layout(title=title)
    return fig


# Labels insights
def series_distribution_plot(series, labels, bin_size=0.0001, fig_width=900, fig_height=550):
    ''' Plot trades distribution and approx distribution curve.
    Takes as an input df_trades from stratgy pnl, bin_size (default 1bp) and gross return as metrix
    '''

    fig = ff.create_distplot([series.values], labels, bin_size=bin_size, show_rug=False)
    # Add shapes
    avg = np.mean(series)
    stdev = np.std(series)

    fig.add_shape(type="line", yref='paper',
        x0=avg, y0=0, x1=avg, y1=1,
        line=dict(color="RoyalBlue",width=2)
    )

    fig.add_shape(type="line", yref='paper',
        x0=avg+stdev, y0=0, x1=avg+stdev, y1=1,
        line=dict(color="RoyalBlue",width=2, dash="dot")
    )

    fig.add_shape(type="line", yref='paper',
        x0=avg-stdev, y0=0, x1=avg-stdev, y1=1,
        line=dict(color="RoyalBlue",width=2, dash="dot")
    )

    fig.add_shape(type="line", yref='paper',
        x0=0, y0=0, x1=0, y1=1,
        line=dict(color="rgba(0, 0, 0, 0.5)",width=2, dash="dashdot")
    )

    fig.update_layout(title=f"<b>{labels} distribution</b>", width=fig_width, height=fig_height, xaxis=dict(tickformat=',.3%'))
    return fig    


def qq_plot(series):

    qqplot_data = qqplot(series, line='s').gca().lines

    fig = go.Figure()

    fig.add_trace({
        'type': 'scatter',
        'x': qqplot_data[0].get_xdata(),
        'y': qqplot_data[0].get_ydata(),
        'mode': 'markers',
        'marker': {
            'color': '#19d3f3'
        }
    })

    fig.add_trace({
        'type': 'scatter',
        'x': qqplot_data[1].get_xdata(),
        'y': qqplot_data[1].get_ydata(),
        'mode': 'lines',
        'line': {
            'color': '#636efa'
        }

    })


    fig['layout'].update({
        'title': 'Quantile-Quantile Plot',
        'xaxis': {
            'title': 'Theoritical Quantities',
            'zeroline': False
        },
        'yaxis': {
            'title': 'Sample Quantities'
        },
        'showlegend': False,
        'width': 800,
        'height': 700,
    })

    fig.show()