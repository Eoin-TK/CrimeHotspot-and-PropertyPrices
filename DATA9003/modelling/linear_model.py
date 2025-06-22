import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import statsmodels.api as sm
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

def TrainTest(X, y, t):
    # for each quarter in t split the data into training (80%) and test (20%) sets

    for quarter in t.unique():
        X_t = X.loc[(t == quarter)]
        y_t = y.loc[(t == quarter)]
        t_t = t.loc[(t == quarter)]

        X_train_t, X_test_t, y_train_t, y_test_t, t_train_t, t_test_t = train_test_split(X_t, y_t, t_t, test_size=0.2, random_state=1)

        # concatenate the sets for each time set to get overall training and test set
        if "X_train" not in locals():
            X_train = X_train_t
            X_test = X_test_t
            y_train = y_train_t
            y_test = y_test_t
            t_train = t_train_t
            t_test = t_test_t
        else:
            X_train = pd.concat([X_train, X_train_t])
            X_test = pd.concat([X_test, X_test_t])
            y_train = pd.concat([y_train, y_train_t])
            y_test = pd.concat([y_test, y_test_t])
            t_train = pd.concat([t_train, t_train_t])
            t_test = pd.concat([t_test, t_test_t])

    return X_train, X_test, y_train, y_test, t_train, t_test

class RollingRegression:
    # steps to initialise an instance of the Rolling Regression Model
    def __init__(self, X, y, t):
        # initialise window width and step size of sliding window
        self.window = 4
        self.stepsize = 1

        # store all data as instance variables
        self.data = X
        self.response = y
        self.time = t

        # some basic error checking
        n_obs = X.shape[0]
        if (len(t) != n_obs):
            raise ValueError("t should be of length {} but is of length {}".format(n_obs, len(t)))
        if (len(y) != n_obs):
            raise ValueError("y should be of length {} but is of length {}".format(n_obs, len(y)))

        # calculate the number of windows needed to cover the entire data set
        n_endog = X.shape[1]
        n_windows = (len(t.unique()) // self.stepsize) - (self.window - self.stepsize)

        # initialise arrays for output to 0
        self.coeffs = np.zeros((n_windows, n_endog))
        self.pvals = np.zeros((n_windows, n_endog))
        self.Rsq = np.zeros(n_windows)
        self.Rsq_adj = np.zeros(n_windows)
        self.Fstat = np.zeros(n_windows)

    # function to fit the RR model
    def fit(self):
        # indices
        idx = 0
        lwr = 0
        upr = self.window

        # iterate through the data set
        while upr <= len(self.time.unique()):
            window = list(self.time.unique())[lwr:upr]

            # filter for data in the current windoe
            x_window = self.data.loc[self.time.isin(window), :]
            y_window = self.response.loc[self.time.isin(window)]

            # fit a linear regression model to the window
            model_window = sm.OLS(y_window, x_window, hasconst=True)
            res_window = model_window.fit()

            # add the coefficients and evaluation metrics to the relevant arrays
            self.coeffs[idx] = np.array(res_window.params)
            self.pvals[idx] = np.array(res_window.pvalues)
            self.Fstat[idx] = np.array(res_window.fvalue)
            self.Rsq[idx] = np.array(res_window.rsquared)
            self.Rsq_adj[idx] = np.array(res_window.rsquared_adj)

            # update indices
            lwr = lwr + self.stepsize
            upr = upr + self.stepsize
            idx = idx + 1

        # convert 2D arrays to dataframes
        self.coeffs = pd.DataFrame(self.coeffs,
                                   columns=self.data.columns)
        self.pvals = pd.DataFrame(self.pvals,
                                  columns=self.data.columns)

    # function to predict the sale price of new observations using the fitted model
    def predict(self, X, t):
        # initialise array for output
        ypred = np.zeros(len(X))

        # iterate through the observations by index
        for i in range(len(X)):
            # get the attribute values
            obs_i = np.array(X.iloc[i, :])

            # get the relevant coefficients for the time
            # any quarters before Q4-2006 use the coeffs for Q4-2006
            if t.iloc[i] <= 3:
                beta = self.coeffs.iloc[0, :]
            else:
                beta = self.coeffs.iloc[t.iloc[i] - 4, :]

            # calculate the estimate for this observation
            ypred[i] = np.dot(obs_i, beta)

        return ypred

    # function to plot the coefficients over time
    def PlotCoefficients(self, coeff=None):
        time = self.coeffs.index

        # define legend elements: green dot = yes, red dot = no
        legend_elements = [Line2D([0], [0],
                                  marker="o",
                                  color="w",
                                  markerfacecolor="green",
                                  markersize=15,
                                  label="Yes"),
                           Line2D([0], [0],
                                  marker="o",
                                  color="w",
                                  markerfacecolor="red",
                                  markersize=15,
                                  label="No")]

        # if a coefficient isn't specified then plot all coeffs in a grid
        if coeff is None:
            fig, ax = plt.subplots(5, 2, figsize=(40, 50))

            # grid indices
            row = 0
            col = 0

            # add a plot of each coeff to the grid
            # colour code points based on their significance at 5%: Green = Yes, Red = No
            for beta in self.coeffs.columns:
                pass_ = self.pvals[beta] <= 0.05
                fail_ = self.pvals[beta] > 0.05

                ax[row, col].plot(time, self.coeffs[beta], c="black", linestyle="--", zorder=1)
                ax[row, col].scatter(time[pass_], self.coeffs.loc[pass_, beta], c="green", zorder=2, s=150)
                ax[row, col].scatter(time[fail_], self.coeffs.loc[fail_, beta], c="red", zorder=3, s=150)
                ax[row, col].set_title(beta, fontsize=50)
                ax[row, col].tick_params(axis='x', labelsize=35)
                ax[row, col].tick_params(axis='y', labelsize=35)

                #update indices
                row = row + 1
                if (row > 4) and (col == 0):
                    col = 1
                    row = 0

        # if a coefficient is specified then plot only that coefficient
        else:
            pass_ = self.pvals[coeff] <= 0.05
            fail_ = self.pvals[coeff] > 0.05

            plt.figure(figsize=(20, 5))
            plt.plot(time, self.coeffs[coeff], c="black", zorder=1)
            plt.scatter(time[pass_], self.coeffs.loc[pass_, coeff], c="green", s=100, zorder=2)
            plt.scatter(time[fail_], self.coeffs.loc[fail_, coeff], c="red", s=100, zorder=3)
            plt.legend(handles=legend_elements, title="Significant at 5%:", fontsize=15, title_fontsize=15)
            plt.grid()
            plt.xlabel("time [quarter]", fontsize=15)
            plt.ylabel("beta [$ (USD)]", fontsize=15)
            plt.title(coeff, fontsize=30)
            plt.xticks(fontsize=18)
            plt.yticks(fontsize=18)
