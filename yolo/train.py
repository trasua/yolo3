import tensorflow as tf
tf.enable_eager_execution()
# print(tf.executing_eagerly())
import os
import h5py
from tqdm import tqdm
from datetime import datetime, date
import time

from yolo.loss import loss_fn
from .utils.utils import EarlyStopping


def train_fn(model,
             train_generator, 
             valid_generator=None, 
             learning_rate=1e-4, 
             num_epoches=500, 
             save_dir=None, 
             weight_name='weights'):
    
    save_file = _setup(save_dir=save_dir, weight_name=weight_name)
    es = EarlyStopping(patience=10)
    optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)

    epoch = -1
    history = []

    current_time = date.today().strftime('%d/%m/%Y-') + datetime.now().strftime('%H:%M:%S')
    writer_1 = tf.contrib.summary.create_file_writer('logs/%s/valid_loss' % current_time, flush_millis=10000)
    writer_2 = tf.contrib.summary.create_file_writer('logs/%s/train_loss' % current_time, flush_millis=10000)

    for idx in range(epoch + 1, num_epoches):
        # 1. update params
        train_loss = _loop_train(model, optimizer, train_generator, idx)
        
        # 2. monitor validation loss
        # with tf.name_scope('loss'):
        if valid_generator:
            val_loss = _loop_validation(model, valid_generator)
            valid_loss = val_loss
        else:
            valid_loss = train_loss

        tensorboard_logger(writer_1, writer_2, train_loss, valid_loss, idx)
        print("{}-th loss = {}, train_loss = {}".format(idx, valid_loss, train_loss))

        # 3. update weights
        history.append(valid_loss)
        if save_file is not None and valid_loss == min(history):
            print("    update weight with loss: {}".format(valid_loss))
            _save_weights(model, '{}.h5'.format(save_file))
            # model.save_weights('{}'.format(save_file), save_format='h5')
        
        if es.step(valid_loss):
            print('early stopping')
            return history
        
    return history


def _loop_train(model, optimizer, generator, epoch):
    # one epoch
    
    n_steps = generator.steps_per_epoch
    loss_value = 0
    for _ in tqdm(range(n_steps)):
        xs, yolo_1, yolo_2, yolo_3 = generator.next_batch()
        ys = [yolo_1, yolo_2, yolo_3]
        grads, loss = _grad_fn(model, xs, ys)
        loss_value += loss
        optimizer.apply_gradients(zip(grads, model.trainable_variables))
    loss_value /= generator.steps_per_epoch
    return loss_value


def _grad_fn(model, images_tensor, list_y_trues):
    with tf.GradientTape() as tape:
        logits = model(images_tensor)
        loss = loss_fn(list_y_trues, logits)
    grads = tape.gradient(loss, model.trainable_variables)
    return grads , loss


def _loop_validation(model, generator):
    # one epoch
    n_steps = generator.steps_per_epoch
    loss_value = 0
    for _ in range(n_steps):
        xs, yolo_1, yolo_2, yolo_3 = generator.next_batch()
        ys = [yolo_1, yolo_2, yolo_3]
        ys_ = model(xs)
        loss_value += loss_fn(ys, ys_)
    loss_value /= generator.steps_per_epoch
    return loss_value


def _setup(save_dir, weight_name='weights'):
    if save_dir:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        file_name = os.path.join(save_dir, weight_name)
    else:
        file_name = None
    return file_name


def _save_weights(model, filename):
    f = h5py.File(filename, 'w')
    weights = model.get_weights()
    for i in range(len(weights)):
        f.create_dataset('weight' + str(i), data=weights[i])
    f.close()


def tensorboard_logger(writer_1, writer_2, train_loss, valid_loss, idx):

    with writer_1.as_default(), tf.contrib.summary.always_record_summaries():
        tf.contrib.summary.scalar('loss', valid_loss, step=idx)
    tf.contrib.summary.flush()

    with writer_2.as_default(), tf.contrib.summary.always_record_summaries():
        tf.contrib.summary.scalar('loss', train_loss, step=idx)
    tf.contrib.summary.flush()


if __name__ == '__main__':
    pass
