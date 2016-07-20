import os
import sqlite3


class PipelineDatabaseError(Exception):
	def __init__(self, msg):
		super(PipelineDatabaseError, self).__init__()
		self.msg = msg


class PipelineDatabase(object):
	def __init__(self, config):
		if config.db == "mysql":
			pass  # TODO: determine best production grade relational database to use

		elif config.db == "sqlite":
			self._dbConn = sqlite3.connect(os.path.join(os.path.dirname(config.path), "isb-cgc-pipelines.db"))

		self._pipelinesDb = self._dbConn.cursor()

	def __del__(self):
		self._dbConn.close()

	def closeConnection(self):
		self._dbConn.close()

	def insertJob(self, *args):
		try:
			self._pipelinesDb.execute("INSERT INTO jobs (operation_id, instance_name, pipeline_name, tag, current_status, preemptions, gcs_log_path, stdout_log, stderr_log, create_time, end_time, processing_time, request) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(args))
			self._dbConn.commit()
		except sqlite3.Error as e:
			raise PipelineDatabaseError("Couldn't create job record: {reason}".format(reason=e))

		return self._pipelinesDb.lastrowid

	def insertJobDependency(self, parentId, childId):
		try:
			self._pipelinesDb.execute("INSERT INTO job_dependencies (parent_id, child_id) VALUES (?,?)", (parentId, childId))
			self._dbConn.commit()
		except sqlite3.Error as e:
			raise PipelineDatabaseError("Couldn't create job dependency record: {reason}".format(reason=e))

	def updateJob(self, key, setValues, keyName="operation_id"):  # setValues -> dict
		if "preemptions" in setValues.keys():
			query = "UPDATE jobs SET preemptions = preemptions + 1 WHERE {key} = ?".format(key=keyName)
			try:
				self._pipelinesDb.execute(query, (key,))

			except sqlite3.Error as e:
				raise PipelineDatabaseError("Couldn't update job record: {reason}".format(reason=e))

			else:
				self._dbConn.commit()

			setValues.pop("preemptions")

		query = "UPDATE jobs SET {values} WHERE {key} = ?".format(key=keyName, values=','.join(["{v} = ?".format(v=v) for v in setValues.iterkeys()]))

		try:
			self._pipelinesDb.execute(query, tuple(setValues.itervalues()) + (key,))

		except sqlite3.Error as e:
			raise PipelineDatabaseError("Couldn't update job record: {reason}".format(reason=e))

		else:
			self._dbConn.commit()


	def getParentJobs(self, childId):
		try:
			parentJobs = self._pipelinesDb.execute("SELECT parent_id FROM job_dependencies WHERE child_id = ?", (childId,)).fetchall()

		except sqlite3.Error as e:
			raise PipelineDatabaseError("Couldn't get parent jobs: {reason}".format(reason=e))

		else:
			return parentJobs

	def getChildJobs(self, parentId):
		try:
			childJobs = self._pipelinesDb.execute("SELECT child_id FROM job_dependencies WHERE parent_id = ?", (parentId,)).fetchall()

		except sqlite3.Error as e:
			raise PipelineDatabaseError("COuldn't get child jobs: {reason}".format(reason=e))

		else:
			return childJobs

	def getJobInfo(self, select=None, where=None, operation="intersection"):  # select -> list, where -> dict
		class JobInfo(object):
			def __init__(self, innerDict):
				self.__dict__.update(innerDict)

		operations = {
			"union": "OR",
			"intersection": "AND"
		}

		query = "SELECT {select} FROM jobs"
		params = []

		if select is None:
			selectString = "*"

		else:
			selectString = ','.join(select)

		if where is None:
			whereString = ""

		else:
			query += " WHERE {where}"
			whereArray = []
			valueArray = []

			for k in where.iterkeys():
				if type(where[k]) == "dict":
					whereArray.append("{k} {comp} ?".format(k=k, comp=where[k]["comparison"]))
					valueArray.append(where[k]["value"])

				else:
					whereArray.append("{k} = ?".format(k=k))
					valueArray.append(where[k])

			whereString = ' {op} '.format(op=operations[operation]).join(whereArray)

			params.extend(valueArray)

		try:
			jobsInfo = self._pipelinesDb.execute(query.format(select=selectString, where=whereString), tuple(params)).fetchall()

		except sqlite3.Error as e:
			raise PipelineDatabaseError("Couldn't get job info: {reason}".format(reason=e))

		jobsList = []
		for j in jobsInfo:
			newDict = {}
			if select is None:
				select = ["job_id", "operation_id", "pipeline_name", "tag", "current_status", "preemptions", "gcs_log_path", "stdout_log", "stderr_log", "create_time", "end_time", "processing_time", "request"]

			for i, k in enumerate(select):
				newDict[k] = j[i]

			jobsList.append(JobInfo(newDict))

		return jobsList

	def createJobTables(self):
		if len(self._pipelinesDb.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="jobs"').fetchall()) == 0:
			query = (
				'CREATE TABLE jobs (job_id INTEGER PRIMARY KEY AUTOINCREMENT, '
				'operation_id VARCHAR(128), '
				'instance_name VARCHAR(128), '
				'pipeline_name VARCHAR(128), '
				'tag VARCHAR(128), '
				'current_status VARCHAR(128), '
				'preemptions INTEGER, '
				'gcs_log_path VARCHAR(128), '
				'stdout_log VARCHAR(128), '
				'stderr_log VARCHAR(128), '
				'create_time VARCHAR(128), '
				'end_time VARCHAR(128), '
				'processing_time FLOAT, '
				'request TEXT)'
			)
			try:
				self._pipelinesDb.execute(query)
				self._dbConn.commit()

			except sqlite3.Error as e:
				raise PipelineDatabaseError("Couldn't create jobs table: {reason}".format(reason=e))

		if len(self._pipelinesDb.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="job_dependencies"').fetchall()) == 0:
			try:
				self._pipelinesDb.execute("CREATE TABLE job_dependencies (row_id INTEGER PRIMARY KEY AUTOINCREMENT, parent_id INTEGER, child_id INTEGER)")
				self._dbConn.commit()

			except sqlite3.Error as e:
				raise PipelineDatabaseError("Couldn't create job dependency table: {reason}".format(reason=e))

		if len(self._pipelinesDb.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="job_archive"').fetchall()) == 0:
			query = (
				'CREATE TABLE job_archive (row_id INTEGER PRIMARY KEY AUTOINCREMENT, '
				'job_id INTEGER, '
				'operation_id VARCHAR(128), '
				'instance_name VARCHAR(128), '
				'pipeline_name VARCHAR(128), '
				'tag VARCHAR(128), '
				'current_status VARCHAR(128), '
				'preemptions INTEGER, '
				'gcs_log_path VARCHAR(128), '
				'stdout_log VARCHAR(128), '
				'stderr_log VARCHAR(128), '
				'create_time VARCHAR(128), '
				'end_time VARCHAR(128), '
				'processing_time FLOAT, '
				'request TEXT)'
			)
			try:
				self._pipelinesDb.execute(query)
				self._dbConn.commit()

			except sqlite3.Error as e:
				raise PipelineDatabaseError("Couldn't create job archive table: {reason}".format(reason=e))