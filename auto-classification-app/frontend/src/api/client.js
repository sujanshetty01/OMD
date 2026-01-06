import axios from "axios";

const API_URL = `http://${window.location.hostname}:8000/api`;

export const uploadDataset = async (file, clientId) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("client_id", clientId);
  const response = await axios.post(`${API_URL}/datasets/upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const getDatasets = async () => {
  const response = await axios.get(`${API_URL}/datasets`);
  return response.data;
};

export const getDataset = async (id) => {
  const response = await axios.get(`${API_URL}/datasets/${id}`);
  return response.data;
};

export const getColumns = async (id) => {
  const response = await axios.get(`${API_URL}/datasets/${id}/columns`);
  return response.data;
};

export const triggerSync = async () => {
    const response = await axios.post(`${API_URL}/system/sync`);
    return response.data;
};

export const applyTag = async (datasetId, columnName, tagFqn) => {
  const response = await axios.post(`${API_URL}/datasets/${datasetId}/columns/${columnName}/tags`, {
    tag_fqn: tagFqn,
    label_type: "Manual"
  });
  return response.data;
};

export const syncFromOM = async (datasetFqn, clientId) => {
  const response = await axios.post(`${API_URL}/sources/om-sync`, {
    dataset_fqn: datasetFqn,
    client_id: clientId
  });
  return response.data;
};

export const listS3Buckets = async () => {
  const response = await axios.get(`${API_URL}/sources/s3/buckets`);
  return response.data.buckets;
};

export const listS3Objects = async (bucket) => {
  const response = await axios.get(`${API_URL}/sources/s3/buckets/${bucket}/objects`);
  return response.data.objects;
};

export const ingestFromS3 = async (bucket, key, clientId) => {
  const response = await axios.post(`${API_URL}/sources/s3/ingest`, {
    bucket,
    key,
    client_id: clientId
  });
  return response.data;
};

export const ingestAllFromS3 = async (bucket, clientId) => {
  const response = await axios.post(`${API_URL}/sources/s3/ingest-all`, {
    bucket,
    client_id: clientId
  });
  return response.data;
};
