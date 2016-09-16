# Copyright (c) 2015-2016, NVIDIA CORPORATION.  All rights reserved.
from __future__ import absolute_import

import flask

from .forms import HdfsImageDatasetForm
from .job import HdfsImageDatasetJob
from digits import utils
from digits.dataset import tasks
from digits.webapp import scheduler
from digits.utils.forms import fill_form_if_cloned, save_form_to_job
from digits.utils.routing import request_wants_json, job_from_request

blueprint = flask.Blueprint(__name__, __name__)

@blueprint.route('/new', methods=['GET'])
@utils.auth.requires_login
def new():
    """
    Returns a form for a new GenericImageDatasetJob
    """
    form = HdfsImageDatasetForm()

    ## Is there a request to clone a job with ?clone=<job_id>
    fill_form_if_cloned(form)

    return flask.render_template('datasets/images/hdfs/new.html', form=form)

@blueprint.route('.json', methods=['POST'])
@blueprint.route('', methods=['POST'], strict_slashes=False)
@utils.auth.requires_login(redirect=False)
def create():
    """
    Creates a new GenericImageDatasetJob

    Returns JSON when requested: {job_id,name,status} or {errors:[]}
    """
    form = HdfsImageDatasetForm()

    ## Is there a request to clone a job with ?clone=<job_id>
    fill_form_if_cloned(form)

    if not form.validate_on_submit():
        if request_wants_json():
            return flask.jsonify({'errors': form.errors}), 400
        else:
            return flask.render_template('datasets/images/hdfs/new.html', form=form), 400

    job = None
    try:
        job = HdfsImageDatasetJob(
                username    = utils.auth.get_username(),
                name        = form.dataset_name.data,
                mean_file   = form.prebuilt_mean_file.data.strip(),
                )

        if form.method.data == 'prebuilt':
            pass
        else:
            raise ValueError('method not supported')

        force_same_shape = form.force_same_shape.data
        h5keys = form.prebuilt_train_labels.data

        job.tasks.append(
                tasks.HdfsDbTask(
                    job_dir     = job.dir(),
                    database_hdfs_path     = form.prebuilt_train_images.data,
                    h5_file_field = h5keys,
                    purpose     = 'Training Images',
                    force_same_shape = force_same_shape,
                    )
                )

        if form.prebuilt_val_images.data:
            job.tasks.append(
                    tasks.HdfsDbTask(
                        job_dir     = job.dir(),
                        database_hdfs_path    = form.prebuilt_val_images.data,
                        h5_file_field = h5keys,
                        purpose   = 'Validation Images',
                        force_same_shape = force_same_shape,
                        )
                    )

        ## Save form data with the job so we can easily clone it later.
        save_form_to_job(job, form)

        scheduler.add_job(job)

        if request_wants_json():
            return flask.jsonify(job.json_dict())
        else:
            return flask.redirect(flask.url_for('digits.dataset.views.show', job_id=job.id()))

    except:
        if job:
            scheduler.delete_job(job)
        raise

def show(job, related_jobs=None):
    """
    Called from digits.dataset.views.datasets_show()
    """
    return flask.render_template('datasets/images/hdfs/show.html', job=job, related_jobs=related_jobs)


def summary(job):
    """
    Return a short HTML summary of a GenericImageDatasetJob
    """
    return flask.render_template('datasets/images/hdfs/summary.html',
                                 dataset=job)
