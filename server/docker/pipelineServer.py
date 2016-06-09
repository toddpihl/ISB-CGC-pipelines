import pickle
import webapp2
from paste import httpserver
from pipelines.builder import PipelineBuilder
from pipelines.schema import PipelineSchema
from pipelines.utils import PipelinesConfig, PipelineDbUtils, PipelineServiceUtils

class ListJobs(webapp2.RequestHandler):
	def get(self):
		# returns a list of jobs matching a filter
		pass


class Job(webapp2.RequestHandler):
	def post(self):
		# submits a job
		args = self.request.get("args")
		config = pickle.loads(self.request.get("config"))
		dbCredentials = pickle.loads(self.request.get("db-credentials"))
		googleCredentials = pickle.loads(self.request.get("google-credentials"))

		if args.scriptUrl:
			pipelineSpec = PipelineSchema(args.pipelineName, config, args.logsPath, args.imageName,
					scriptUrl=args.scriptUrl, cores=args.cores,
					mem=args.mem, diskSize=args.diskSize, diskType=args.diskType, env=args.env,
					inputs=args.inputs, outputs=args.outputs, tag=args.tag,
					preemptible=args.preemptible)
		elif args.cmd:
			pipelineSpec = PipelineSchema(args.pipelineName, config, args.logsPath, args.imageName, cmd=args.cmd,
				cores=args.cores,
				mem=args.mem, diskSize=args.diskSize, diskType=args.diskType, env=args.env,
				inputs=args.inputs, outputs=args.outputs, tag=args.tag,
				preemptible=args.preemptible)

		# TODO: translate code below into a server request; move the code below to the server
		pipelineBuilder = PipelineBuilder(config)
		pipelineBuilder.addStep(pipelineSpec)
		pipelineBuilder.run(dbCredentials, googleCredentials)

	def get(self):
		# gets the status of a particular job
		pass

	def put(self):
		# updates a job attribute
		pass

	def delete(self):
		# deletes a job
		pass


app = webapp2.WSGIApplication([
	(r'/jobs', ListJobs),
	(r'/jobs/(\d+)', Job),
], debug=True)


def main():
	httpserver.serve(app, host='0.0.0.0', port='8080')


if __name__ == "__main__":
	main()
