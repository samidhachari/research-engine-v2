import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000",
});

export const generateResearch = async (
  topic,
  mode
) => {
  const response = await API.post(
    "/research",
    {
      topic,
      mode,
    }
  );

  return response.data;
};

export default API;