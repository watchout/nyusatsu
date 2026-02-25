import { useParams } from 'react-router-dom'

function CaseDetail() {
  const { id } = useParams()
  return (
    <div>
      <h1>Case Detail</h1>
      <p>Case ID: {id}</p>
      <p>Coming soon</p>
    </div>
  )
}

export default CaseDetail
