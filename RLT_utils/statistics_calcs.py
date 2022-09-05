from numpy.random import seed
from numpy.random import randn
from scipy.stats import shapiro, normaltest, anderson

def shapiro_norm_test(series):
# normality test
    stat, p = shapiro(series)
    print('Statistics=%.3f, p=%.3f' % (stat, p))
    # interpret
    alpha = 0.05
    if p > alpha:
        print('Sample looks Gaussian (fail to reject H0)')
    else:
        print('Sample does not look Gaussian (reject H0)')

def dagostino_norm_test(series):
    # normality test
    stat, p = normaltest(series)
    print('Statistics=%.3f, p=%.3f' % (stat, p))
    # interpret
    alpha = 0.05
    if p > alpha:
        print('Sample looks Gaussian (fail to reject H0)')
    else:
        print('Sample does not look Gaussian (reject H0)')

def anderson_darling_norm_test(series):
    # normality test
    result = anderson(series)
    print('Statistic: %.3f' % result.statistic)
    p = 0
    for i in range(len(result.critical_values)):
        sl, cv = result.significance_level[i], result.critical_values[i]
        if result.statistic < result.critical_values[i]:
            print('%.3f: %.3f, data looks normal (fail to reject H0)' % (sl, cv))
        else:
            print('%.3f: %.3f, data does not look normal (reject H0)' % (sl, cv))

def run_normality_tests(series):
    '''
    Statistic: A quantity calculated by the test that can be interpreted in the context of the test via comparing it to critical values 
        from the distribution of the test statistic.
    p-value: Used to interpret the test, in this case whether the sample was drawn from a Gaussian distribution.
    p <= alpha: reject H0, not normal.
    p > alpha: fail to reject H0, normal.
    '''
    
    shapiro_norm_test(series)
    dagostino_norm_test(series)
    anderson_darling_norm_test(series)