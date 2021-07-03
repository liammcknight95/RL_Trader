from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import Input, Reshape, Conv2D, LSTM, Dense, MaxPooling2D, BatchNormalization, LeakyReLU, concatenate, add, Dropout, Flatten
from tensorflow.keras.optimizers import Adam

def create_light_deeplob(T, lob_depth):
    ## just a test

    input_lmd = Input(shape=(T, lob_depth * 4, 1))
    conv_first1 = Conv2D(16, (1, 2), strides=(1, 2))(input_lmd)
    conv_first1 = LeakyReLU(alpha=0.01)(conv_first1)    
    conv_first1 = BatchNormalization()(conv_first1)
    # conv_first1 = Dropout(.5)(conv_first1)
    
    # note on learnable parameters: CONV2(filter shape =1*2, stride=1) layer is: ((shape of width of filter * shape of height filter * number of filters in the previous layer+1) * number of filters) = 2080 or ((2*1*32)+1)*32
    conv_first1 = Conv2D(16, (1, 2), strides=(1, 2))(conv_first1)
    conv_first1 = LeakyReLU(alpha=0.01)(conv_first1)
    conv_first1 = BatchNormalization()(conv_first1)

    conv_first1 = Conv2D(16, (1, lob_depth))(conv_first1)
    conv_first1 = LeakyReLU(alpha=0.01)(conv_first1)
    conv_first1 = BatchNormalization()(conv_first1)
    print(conv_first1.shape)

    convfirst_output = Reshape((int(conv_first1.shape[1])* int(conv_first1.shape[3]),))(conv_first1)
    print(convfirst_output.shape)
    # note on learnable parameters:FC3 layer is((current layer c*previous layer p)+1*c) with c being number of neurons
    out = Dense(3, activation='softmax')(convfirst_output)
    print(out.shape)
    model = Model(inputs=input_lmd, outputs=out)
    adam = Adam(lr=0.1, beta_1=0.9, beta_2=0.999, epsilon=1e-07)
    model.compile(optimizer=adam, loss='categorical_crossentropy', metrics=['accuracy'])

    return model


def mlp(timestep, n_features):
    ## mlp baseline experiment

    input_layer = Input(timestep, n_features)
    flattened_input = Flatten()(input_layer)
    dense_1 = Dense((timestep/2)*n_features)(flattened_input)
    dense_2 = Dense((timestep/4)*n_features)(dense_1)
    dense_3 = Dense(int(timestep/8)*n_features)(dense_2)

    out = Dense(3, activation='softmax')(dense_3)
    print(out.shape)

    model = Model(inputs=input_layer, outputs=out)
    adam = Adam(lr=0.1, beta_1=0.9, beta_2=0.999, epsilon=1e-07)
    model.compile(optimizer=adam, loss='categorical_crossentropy', metrics=['accuracy'])


